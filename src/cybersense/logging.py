"""Structured JSON logging for CyberSense."""

from __future__ import annotations

import logging
import sys
from typing import Any

try:
    import json

    class _JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:  # noqa: A003
            base: dict[str, Any] = {
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                base["exc_info"] = self.formatException(record.exc_info)
            # Copy any extra fields attached to the record
            for key, val in record.__dict__.items():
                if key not in {
                    "args",
                    "asctime",
                    "created",
                    "exc_info",
                    "exc_text",
                    "filename",
                    "funcName",
                    "id",
                    "levelname",
                    "levelno",
                    "lineno",
                    "message",
                    "module",
                    "msecs",
                    "msg",
                    "name",
                    "pathname",
                    "process",
                    "processName",
                    "relativeCreated",
                    "stack_info",
                    "thread",
                    "threadName",
                }:
                    base[key] = val
            return json.dumps(base, default=str)

except Exception:
    _JsonFormatter = logging.Formatter  # type: ignore[misc,assignment]


def setup_logging(level: str = "INFO", use_json: bool = True) -> None:
    """Configure root logger; call once at application startup."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _JsonFormatter()
        if use_json
        else logging.Formatter("%(asctime)s %(levelname)-8s %(name)s  %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
