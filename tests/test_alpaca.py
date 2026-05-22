import pytest

from src.ai_investing.alpaca import (
    AlpacaPaperCredentials,
    account_summary_from_payload,
    alpaca_order_payload,
    decimal_string,
    ensure_paper_credentials,
    mask_account_number,
    paper_order_result_from_payload,
    paper_orders_from_payload,
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


def test_ensure_paper_credentials_blocks_live_url():
    with pytest.raises(RuntimeError, match="alpaca_paper_only_guard_failed"):
        ensure_paper_credentials(AlpacaPaperCredentials("key", "secret", "https://api.alpaca.markets"))


def test_ensure_paper_credentials_requires_key_and_secret():
    with pytest.raises(RuntimeError, match="alpaca_paper_credentials_missing"):
        ensure_paper_credentials(AlpacaPaperCredentials("", "", "https://paper-api.alpaca.markets"))


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
