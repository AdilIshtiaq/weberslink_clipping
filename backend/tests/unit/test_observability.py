import json
import logging

from src import observability


def _record(name="src.test", exc_info=None):
    record = logging.LogRecord(name, logging.ERROR, __file__, 1, "boom", None, exc_info)
    observability.TraceIdFilter().filter(record)
    return record


def test_logs_carry_service_trace_and_user():
    observability.set_trace_id("trace-1")
    observability.set_user_id("user-1")
    try:
        payload = json.loads(observability.JsonLogFormatter().format(_record()))
    finally:
        observability.clear_trace_id()
        observability.set_user_id(None)

    assert payload["trace_id"] == "trace-1"
    assert payload["user_id"] == "user-1"
    assert payload["service"] == observability.SERVICE_NAME


def test_logs_omit_user_when_unauthenticated():
    payload = json.loads(observability.JsonLogFormatter().format(_record()))
    assert "user_id" not in payload
