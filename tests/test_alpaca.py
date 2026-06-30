import pytest

from src.ai_investing.alpaca import (
    AlpacaMarketDataCredentials,
    AlpacaPaperCredentials,
    account_summary_from_payload,
    alpaca_bracket_order_payload,
    alpaca_order_payload,
    decimal_string,
    ensure_market_data_credentials,
    ensure_paper_credentials,
    mask_account_number,
    market_snapshot_from_alpaca_payload,
    paper_clock_from_payload,
    paper_order_result_from_payload,
    paper_orders_from_payload,
    paper_position_from_payload,
    paper_positions_from_payload,
)
from src.ai_investing.models import OrderProposal, Side


def test_mask_account_number_keeps_only_last_four():
    assert mask_account_number("ABC123456789") == "********6789"
    assert mask_account_number("123") == "***"
    assert mask_account_number(None) is None


def test_decimal_string_normalizes_numeric_payload_values():
    assert decimal_string("1000.50") == "1000.50"
    assert decimal_string(None) == "0"
    assert decimal_string("not-a-number") == "0"


def test_account_summary_from_payload_masks_sensitive_fields():
    summary = account_summary_from_payload(
        {
            "status": "ACTIVE",
            "currency": "USD",
            "buying_power": "100000",
            "cash": "100000",
            "portfolio_value": "100000",
            "pattern_day_trader": False,
            "account_number": "PA123456789",
        }
    )
    assert summary.status == "ACTIVE"
    assert summary.currency == "USD"
    assert summary.buying_power == "100000"
    assert summary.account_number_masked == "*******6789"


def test_alpaca_order_payload_is_paper_limit_day_order():
    payload = alpaca_order_payload(
        OrderProposal(
            symbol="QQQ",
            side=Side.BUY,
            quantity=0.12345678,
            limit_price=430.129,
            expected_edge_bps=10.0,
            reason="test",
        )
    )
    assert payload == {
        "symbol": "QQQ",
        "qty": "0.12345678",
        "side": "buy",
        "type": "limit",
        "time_in_force": "day",
        "limit_price": "430.13",
        "extended_hours": False,
    }


def test_alpaca_order_payload_rejects_invalid_order_values():
    order = OrderProposal("QQQ", Side.BUY, 0.0, 430.0, 10.0, "test")
    with pytest.raises(ValueError, match="order_quantity_must_be_positive"):
        alpaca_order_payload(order)


def test_alpaca_bracket_order_payload_attaches_bounded_exits():
    order = OrderProposal("QQQ", Side.BUY, 0.01, 430.0, 12.0, "test")
    payload = alpaca_bracket_order_payload(order, stop_price=423.55, take_profit_price=442.9)

    assert payload["order_class"] == "bracket"
    assert payload["take_profit"] == {"limit_price": "442.90"}
    assert payload["stop_loss"] == {"stop_price": "423.55"}
    assert payload["extended_hours"] is False


def test_alpaca_bracket_order_payload_rejects_unbounded_or_sell_entry():
    sell = OrderProposal("QQQ", Side.SELL, 0.01, 430.0, 12.0, "test")
    with pytest.raises(ValueError, match="bracket_entry_must_be_buy"):
        alpaca_bracket_order_payload(sell, stop_price=423.55, take_profit_price=442.9)

    buy = OrderProposal("QQQ", Side.BUY, 0.01, 430.0, 12.0, "test")
    with pytest.raises(ValueError, match="bracket_exit_prices_must_bound_entry"):
        alpaca_bracket_order_payload(buy, stop_price=431.0, take_profit_price=442.9)


def test_ensure_paper_credentials_blocks_live_url():
    with pytest.raises(RuntimeError, match="alpaca_paper_only_guard_failed"):
        ensure_paper_credentials(AlpacaPaperCredentials("key", "secret", "https://api.alpaca.markets"))


def test_ensure_paper_credentials_requires_key_and_secret():
    with pytest.raises(RuntimeError, match="alpaca_paper_credentials_missing"):
        ensure_paper_credentials(AlpacaPaperCredentials("", "", "https://paper-api.alpaca.markets"))


def test_ensure_market_data_credentials_blocks_non_data_url():
    with pytest.raises(RuntimeError, match="alpaca_market_data_guard_failed"):
        ensure_market_data_credentials(AlpacaMarketDataCredentials("key", "secret", "https://api.alpaca.markets"))


def test_ensure_market_data_credentials_rejects_unknown_feed():
    with pytest.raises(RuntimeError, match="alpaca_market_data_feed_not_allowed"):
        ensure_market_data_credentials(
            AlpacaMarketDataCredentials("key", "secret", "https://data.alpaca.markets", "unknown")
        )


def test_market_snapshot_from_alpaca_payload_uses_trade_quote_and_daily_volume():
    snapshot = market_snapshot_from_alpaca_payload(
        "qqq",
        {
            "latestTrade": {"p": 430.12, "t": "2026-05-22T20:00:00Z"},
            "latestQuote": {"bp": 430.1, "ap": 430.2},
            "dailyBar": {"o": 425.0, "v": 12_345_678},
        },
        default_volatility_30d=0.04,
    )
    assert snapshot.symbol == "QQQ"
    assert snapshot.price == 430.12
    assert snapshot.spread_bps == pytest.approx(2.3247704)
    assert snapshot.volume_24h == 12_345_678
    assert snapshot.volatility_30d == 0.04
    assert snapshot.intraday_change_bps == pytest.approx(120.470588)


def test_market_snapshot_from_alpaca_payload_requires_price():
    with pytest.raises(RuntimeError, match="alpaca_market_data_missing_price"):
        market_snapshot_from_alpaca_payload("QQQ", {"latestTrade": {}, "latestQuote": {}, "minuteBar": {}})


def test_paper_order_result_from_payload_masks_to_safe_fields():
    result = paper_order_result_from_payload(
        {
            "id": "order-123",
            "client_order_id": "client-123",
            "status": "accepted",
            "symbol": "QQQ",
            "side": "buy",
            "submitted_at": "2026-05-22T00:00:00Z",
            "sensitive": "ignored",
        }
    )
    assert result.broker_order_id == "order-123"
    assert result.client_order_id == "client-123"
    assert result.status == "accepted"
    assert result.symbol == "QQQ"
    assert result.side == "buy"
    assert result.filled_avg_price is None
    assert result.filled_quantity is None


def test_order_result_preserves_fill_values_for_performance_accounting():
    result = paper_order_result_from_payload(
        {
            "id": "order-123",
            "status": "filled",
            "symbol": "QQQ",
            "side": "sell",
            "filled_avg_price": "703.25",
            "filled_qty": "0.008",
        }
    )

    assert result.filled_avg_price == 703.25
    assert result.filled_quantity == 0.008


def test_paper_orders_from_payload_returns_safe_order_results():
    results = paper_orders_from_payload(
        [
            {
                "id": "order-1",
                "client_order_id": "client-1",
                "status": "accepted",
                "symbol": "QQQ",
                "side": "buy",
                "submitted_at": "2026-05-22T00:00:00Z",
            },
            {
                "id": "order-2",
                "client_order_id": "client-2",
                "status": "filled",
                "symbol": "SPY",
                "side": "sell",
                "submitted_at": "2026-05-22T00:01:00Z",
            },
        ]
    )
    assert [result.broker_order_id for result in results] == ["order-1", "order-2"]
    assert [result.status for result in results] == ["accepted", "filled"]


def test_paper_position_from_payload_normalizes_position_fields():
    position = paper_position_from_payload(
        {
            "symbol": "qqq",
            "qty": "0.0025",
            "market_value": "1.80",
            "avg_entry_price": "720.00",
            "current_price": "721.00",
        }
    )

    assert position.symbol == "QQQ"
    assert position.quantity == 0.0025
    assert position.market_value == 1.8
    assert position.avg_entry_price == 720.0
    assert position.current_price == 721.0


def test_paper_positions_from_payload_returns_safe_positions():
    positions = paper_positions_from_payload(
        [
            {"symbol": "QQQ", "qty": "0.0025"},
            {"symbol": "NVDA", "qty": "0.01"},
        ]
    )

    assert [position.symbol for position in positions] == ["QQQ", "NVDA"]
    assert [position.quantity for position in positions] == [0.0025, 0.01]


def test_paper_clock_from_payload_returns_safe_fields():
    clock = paper_clock_from_payload(
        {
            "timestamp": "2026-05-22T20:00:00Z",
            "is_open": True,
            "next_open": "2026-05-26T13:30:00Z",
            "next_close": "2026-05-22T20:00:00Z",
            "extra": "ignored",
        }
    )

    assert clock.timestamp == "2026-05-22T20:00:00Z"
    assert clock.is_open is True
    assert clock.next_open == "2026-05-26T13:30:00Z"
    assert clock.next_close == "2026-05-22T20:00:00Z"


def test_paper_order_result_from_cancel_body_payload():
    result = paper_order_result_from_payload(
        {
            "id": "order-cancelled",
            "client_order_id": "client-cancelled",
            "status": "canceled",
            "symbol": "QQQ",
            "side": "buy",
            "submitted_at": "2026-05-22T00:00:00Z",
        }
    )
    assert result.broker_order_id == "order-cancelled"
    assert result.status == "canceled"
