"""Tests for structured JSON logging."""

from __future__ import annotations

import io
import json
import logging

from utils.logging import JSONFormatter, get_logger


class TestJSONFormatter:
    """Test the JSON log formatter."""

    def test_formats_as_json(self):
        """Output should be valid JSON."""
        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="x.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = fmt.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_includes_extra_fields(self):
        """Extra dict fields should appear in output."""
        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="x.py",
            lineno=1,
            msg="Task done",
            args=(),
            exc_info=None,
        )
        record.task_id = "t123"
        record.duration = 1.5
        output = fmt.format(record)
        data = json.loads(output)
        assert data["task_id"] == "t123"
        assert data["duration"] == 1.5


class TestGetLogger:
    """Test logger creation."""

    def test_returns_logger(self):
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_writes_json_to_stream(self):
        """Logger should output JSON to stderr."""
        logger = get_logger("test.json_out")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())

        # Clear default handlers and use our test stream
        logger.handlers.clear()
        logger.addHandler(handler)

        logger.info("Hello structured world", extra={"count": 42})

        output = stream.getvalue().strip()
        data = json.loads(output)
        assert data["message"] == "Hello structured world"
        assert data["count"] == 42

    def test_handlers_not_duplicated(self):
        """Calling get_logger twice should not duplicate handlers."""
        a = get_logger("test.dedup")
        b = get_logger("test.dedup")
        assert len(a.handlers) == len(b.handlers)
        assert len(a.handlers) == 1
