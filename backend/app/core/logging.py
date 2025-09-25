"""Logging configuration utilities."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any

from .config import settings

_trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)


def set_trace_id(trace_id: str | None) -> None:
    """Store trace identifier for current context."""
    _trace_id_ctx.set(trace_id)


def get_trace_id() -> str | None:
    return _trace_id_ctx.get()


class JsonLogFormatter(logging.Formatter):
    """Simple JSON log formatter with trace support."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        trace_id = getattr(record, "trace_id", None) or get_trace_id()
        if trace_id:
            payload["trace_id"] = trace_id
        if record.__dict__:
            extra = {k: v for k, v in record.__dict__.items() if k not in logging.LogRecord.__dict__}
            if extra:
                payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Configure root logger for JSON output."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    root.handlers.clear()
    root.addHandler(handler)
    # Quiet chatty libs
    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine", "aioboto3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


__all__ = ["configure_logging", "set_trace_id", "get_trace_id"]
