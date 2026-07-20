"""Tests for Xiaohongshu platform adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from platforms.base import ContentPost
from platforms.xiaohongshu import XiaohongshuAdapter


class TestXiaohongshuAdapter:
    def test_initialization(self):
        adapter = XiaohongshuAdapter({"cookie": "test"})
        assert adapter.platform_name == "xiaohongshu"
        assert adapter.supports_media is True

    def test_authenticate_without_cookie(self):
        assert XiaohongshuAdapter().authenticate() is False

    def test_authenticate_success(self):
        adapter = XiaohongshuAdapter({"cookie": "valid"})
        with patch.object(httpx.Client, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            assert adapter.authenticate() is True

    def test_post_not_authenticated(self):
        result = XiaohongshuAdapter().post(ContentPost(text="Test"))
        assert result.success is False

    def test_post_success(self):
        adapter = XiaohongshuAdapter({"cookie": "test"})
        adapter._authenticated = True
        mock_client = MagicMock()
        mock_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True, "data": {"note_id": "note_abc"}},
        )
        adapter._client = mock_client
        result = adapter.post(ContentPost(text="Content here", title="My Note"))
        assert result.success is True
        assert result.post_id == "note_abc"

    def test_validate_content_ok(self):
        adapter = XiaohongshuAdapter()
        ok, _ = adapter.validate_content(ContentPost(text="A" * 60, title="Title"))
        assert ok is True

    def test_validate_title_too_long(self):
        adapter = XiaohongshuAdapter()
        ok, msg = adapter.validate_content(
            ContentPost(text="A" * 60, title="This is a very long title")
        )
        assert ok is False

    def test_get_status(self):
        status = XiaohongshuAdapter().get_status()
        assert status.platform == "xiaohongshu"
