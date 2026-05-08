import json
import logging

from src.ai_investing.logging_utils import JsonFormatter, request_id_ctx


def test_json_formatter_includes_required_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello world",
        args=(),
        exc_info=None,
    )

    out = formatter.format(record)
    payload = json.loads(out)

    assert "ts" in payload
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert payload["msg"] == "hello world"
    assert "request_id" in payload


def test_request_id_context_is_emitted():
    formatter = JsonFormatter()
    token = request_id_ctx.set("req-123")

    try:
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname=__file__,
            lineno=20,
            msg="context test",
            args=(),
            exc_info=None,
        )
        payload = json.loads(formatter.format(record))
        assert payload["request_id"] == "req-123"
        assert payload["level"] == "WARNING"
    finally:
        request_id_ctx.reset(token)


def test_optional_structured_fields_are_included():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=30,
        msg="structured extras",
        args=(),
        exc_info=None,
    )

    record.event = "request_completed"
    record.endpoint = "/health"
    record.status_code = 200
    record.reason = "ok"
    record.symbol = "QQQ"

    payload = json.loads(formatter.format(record))

    assert payload["event"] == "request_completed"
    assert payload["endpoint"] == "/health"
    assert payload["status_code"] == 200
    assert payload["reason"] == "ok"
    assert payload["symbol"] == "QQQ"