"""Tests for SegmentFault platform adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from platforms.base import ContentPost
from platforms.segmentfault import SegmentFaultAdapter


class TestSegmentFaultAdapter:
    def test_initialization(self):
        adapter = SegmentFaultAdapter({"cookie": "test"})
        assert adapter.platform_name == "segmentfault"

    def test_authenticate_without_cookie(self):
        adapter = SegmentFaultAdapter()
        assert adapter.authenticate() is False

    def test_authenticate_success(self):
        adapter = SegmentFaultAdapter({"cookie": "valid"})
        with patch.object(httpx.Client, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            assert adapter.authenticate() is True

    def test_post_not_authenticated(self):
        adapter = SegmentFaultAdapter()
        result = adapter.post(ContentPost(text="Test"))
        assert result.success is False

    def test_post_success(self):
        adapter = SegmentFaultAdapter({"cookie": "test"})
        adapter._authenticated = True
        mock_client = MagicMock()
        mock_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": 0, "data": {"id": "art_123"}},
        )
        adapter._client = mock_client

        result = adapter.post(ContentPost(text="Content", title="Title"))
        assert result.success is True
        assert result.post_id == "art_123"

    def test_post_api_error(self):
        adapter = SegmentFaultAdapter({"cookie": "test"})
        adapter._authenticated = True
        mock_client = MagicMock()
        mock_client.post.return_value = MagicMock(status_code=500, text="Error")
        adapter._client = mock_client

        result = adapter.post(ContentPost(text="Test", title="T"))
        assert result.success is False

    def test_validate_content_ok(self):
        adapter = SegmentFaultAdapter()
        ok, _ = adapter.validate_content(ContentPost(text="A" * 200, title="Title"))
        assert ok is True

    def test_validate_content_empty(self):
        adapter = SegmentFaultAdapter()
        ok, _ = adapter.validate_content(ContentPost(text=""))
        assert ok is False

    def test_get_status(self):
        adapter = SegmentFaultAdapter()
        status = adapter.get_status()
        assert status.platform == "segmentfault"
