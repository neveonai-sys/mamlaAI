"""
Request context log filter.

Injects request_id and user_id into every log record so they appear
automatically in every log line without needing the request object.

TelemetryMiddleware writes to _request_context before the view runs;
the filter reads from it and falls back to safe defaults.
"""
import logging
import threading

_request_context = threading.local()


def set_log_context(request_id: str, user_id: str) -> None:
    """Called by TelemetryMiddleware at the start of each request."""
    _request_context.request_id = request_id
    _request_context.user_id = user_id


def clear_log_context() -> None:
    """Called by TelemetryMiddleware at the end of each request."""
    _request_context.request_id = "-"
    _request_context.user_id = "-"


class RequestContextFilter(logging.Filter):
    """Injects request_id and user_id into all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(_request_context, "request_id", "-")
        record.user_id = getattr(_request_context, "user_id", "-")
        return True
