import json
import logging
import os
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


TRACE_HEADER = "x-trace-id"
_trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="-")
_user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)

# "backend" or "worker"; set per container so logs and error reports say which
# process they came from.
SERVICE_NAME = os.getenv("WEBERSLINKCLIP_SERVICE", "backend")


def get_trace_id() -> str:
    return _trace_id_ctx.get()


def set_trace_id(trace_id: str) -> None:
    _trace_id_ctx.set(trace_id)


def clear_trace_id() -> None:
    _trace_id_ctx.set("-")


def generate_trace_id() -> str:
    return uuid4().hex


def get_user_id() -> str | None:
    return _user_id_ctx.get()


def set_user_id(user_id: str | None) -> None:
    _user_id_ctx.set(user_id)


def bind_request_user(request: Any, user_id: str) -> None:
    """Attach the authenticated user to the request's logs and error reports.

    The request middleware runs outside the endpoint's context, so the id is
    also kept on ``request.state`` for it to pick up.
    """
    set_user_id(user_id)
    request.state.user_id = user_id


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        record.user_id = get_user_id()
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": SERVICE_NAME,
            "trace_id": getattr(record, "trace_id", "-"),
        }
        user_id = getattr(record, "user_id", None)
        if user_id:
            payload["user_id"] = user_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # YouTube download attempts. These names are stable so log queries can
        # sum bytes per provider. Proxy URLs are never attached to the record.
        for key in (
            "youtube_provider",
            "youtube_video_id",
            "youtube_download_kind",
            "youtube_outcome",
            "youtube_bytes",
            "youtube_fallback",
            "task_id",
            # Task-creation source submissions. Values are sanitized; the raw
            # query string, fragment, and credentials are never attached.
            "source_user_id",
            "source_client",
            "source_type",
            "source_domain",
            "source_url",
            "source_outcome",
            "source_status",
            "source_reason",
        ):
            value = getattr(record, key, None)
            if value not in (None, ""):
                payload[key] = value

        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)

    formatter = JsonLogFormatter()
    trace_filter = TraceIdFilter()

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(trace_filter)

    app_file_handler = logging.FileHandler(logs_dir / "backend.log")
    app_file_handler.setLevel(log_level)
    app_file_handler.setFormatter(formatter)
    app_file_handler.addFilter(trace_filter)

    error_file_handler = logging.FileHandler(logs_dir / "backend-error.log")
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    error_file_handler.addFilter(trace_filter)

    root_logger.addHandler(stream_handler)
    root_logger.addHandler(app_file_handler)
    root_logger.addHandler(error_file_handler)

    for logger_name in ("httpx", "httpcore"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
