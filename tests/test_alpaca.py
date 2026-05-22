from src.ai_investing.alpaca import account_summary_from_payload, decimal_string, mask_account_number


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
