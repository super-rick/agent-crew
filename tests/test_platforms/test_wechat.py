"""Tests for WeChat Public Platform adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from platforms.base import ContentPost
from platforms.wechat import WechatAdapter


class TestWechatAdapter:
    """Test WeChat adapter."""

    def test_initialization(self):
        adapter = WechatAdapter({"app_id": "wx123", "app_secret": "secret"})
        assert adapter.platform_name == "wechat"
        assert adapter.supports_media is True

    def test_authenticate_without_credentials(self):
        adapter = WechatAdapter()
        result = adapter.authenticate()
        assert result is False

    def test_authenticate_success(self):
        adapter = WechatAdapter({"app_id": "wx123", "app_secret": "secret"})
        with patch.object(httpx.Client, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"access_token": "token_abc123"}
            mock_get.return_value = mock_resp
            result = adapter.authenticate()
            assert result is True
            assert adapter._access_token == "token_abc123"

    def test_authenticate_failure(self):
        adapter = WechatAdapter({"app_id": "wx123", "app_secret": "bad"})
        with patch.object(httpx.Client, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"errcode": 40013, "errmsg": "invalid appid"}
            mock_get.return_value = mock_resp
            result = adapter.authenticate()
            assert result is False

    def test_post_not_authenticated(self):
        adapter = WechatAdapter()
        content = ContentPost(text="Test")
        result = adapter.post(content)
        assert result.success is False

    def test_post_empty_content(self):
        adapter = WechatAdapter({"app_id": "x", "app_secret": "y"})
        adapter._authenticated = True
        adapter._client = MagicMock()
        content = ContentPost(text="")
        result = adapter.post(content)
        assert result.success is False

    def test_post_success(self):
        adapter = WechatAdapter({"app_id": "x", "app_secret": "y"})
        adapter._authenticated = True
        adapter._access_token = "tok"
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"media_id": "draft_456"}
        mock_client.post.return_value = mock_resp
        adapter._client = mock_client

        content = ContentPost(text="Content here", title="My Article")
        result = adapter.post(content)

        assert result.success is True
        assert result.post_id == "draft_456"

    def test_post_api_error(self):
        adapter = WechatAdapter({"app_id": "x", "app_secret": "y"})
        adapter._authenticated = True
        adapter._access_token = "tok"
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"errcode": 40001, "errmsg": "invalid token"}
        mock_client.post.return_value = mock_resp
        adapter._client = mock_client

        content = ContentPost(text="Content", title="Title")
        result = adapter.post(content)
        assert result.success is False

    def test_validate_content_ok(self):
        adapter = WechatAdapter()
        ok, _ = adapter.validate_content(ContentPost(text="A" * 400, title="Title"))
        assert ok is True

    def test_validate_content_empty(self):
        adapter = WechatAdapter()
        ok, _ = adapter.validate_content(ContentPost(text=""))
        assert ok is False

    def test_validate_title_too_long(self):
        adapter = WechatAdapter()
        ok, msg = adapter.validate_content(ContentPost(text="A" * 400, title="X" * 65))
        assert ok is False
        assert "Title too long" in msg

    def test_get_status(self):
        adapter = WechatAdapter()
        status = adapter.get_status()
        assert status.platform == "wechat"
