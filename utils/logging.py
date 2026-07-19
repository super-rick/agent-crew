"""Structured JSON logging for AgentCrew MCN.

Provides a simple structured logger that outputs JSON lines.
Use `get_logger(name)` to get a logger instance.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            data["exception"] = str(record.exc_info[1])
        for key, value in record.__dict__.items():
            if key not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
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
                data[key] = value
        return json.dumps(data, ensure_ascii=False)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Get a structured JSON logger.

    Args:
        name: Logger name (typically module or component name).
        level: Log level (DEBUG, INFO, WARNING, ERROR).

    Returns:
        A configured logger that outputs JSON to stderr.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Only add handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger
