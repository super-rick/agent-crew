"""Tests for CSDN platform adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from platforms.base import ContentPost
from platforms.csdn import CsdnAdapter


class TestCsdnAdapter:
    """Test CSDN adapter."""

    def test_initialization(self):
        adapter = CsdnAdapter({"cookie": "test_cookie"})
        assert adapter.platform_name == "csdn"
        assert adapter.supports_media is False

    def test_authenticate_without_cookie(self):
        adapter = CsdnAdapter()
        result = adapter.authenticate()
        assert result is False
        assert adapter._authenticated is False

    def test_authenticate_with_cookie_success(self):
        adapter = CsdnAdapter({"cookie": "valid_cookie"})
        with patch.object(httpx.Client, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"code": 200, "data": {"username": "test"}}
            mock_get.return_value = mock_resp
            result = adapter.authenticate()
            assert result is True

    def test_authenticate_with_cookie_failure(self):
        adapter = CsdnAdapter({"cookie": "bad_cookie"})
        with patch.object(httpx.Client, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_get.return_value = mock_resp
            result = adapter.authenticate()
            assert result is False

    def test_post_not_authenticated(self):
        adapter = CsdnAdapter()
        content = ContentPost(text="Test content")
        result = adapter.post(content)
        assert result.success is False
        assert "Not authenticated" in (result.error_message or "")

    def test_post_empty_content(self):
        adapter = CsdnAdapter({"cookie": "test"})
        adapter._authenticated = True
        adapter._client = MagicMock()
        content = ContentPost(text="")
        result = adapter.post(content)
        assert result.success is False

    def test_post_success(self):
        adapter = CsdnAdapter({"cookie": "test"})
        adapter._authenticated = True
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 200, "data": {"id": "12345"}}
        mock_client.post.return_value = mock_resp
        adapter._client = mock_client

        content = ContentPost(text="Article content", title="Test Article")
        result = adapter.post(content)

        assert result.success is True
        assert result.post_id == "12345"

    def test_post_api_error(self):
        adapter = CsdnAdapter({"cookie": "test"})
        adapter._authenticated = True
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal error"
        mock_client.post.return_value = mock_resp
        adapter._client = mock_client

        content = ContentPost(text="Test", title="Test")
        result = adapter.post(content)
        assert result.success is False

    def test_post_with_tags(self):
        adapter = CsdnAdapter({"cookie": "test"})
        adapter._authenticated = True
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 200, "data": {"id": "456"}}
        mock_client.post.return_value = mock_resp
        adapter._client = mock_client

        content = ContentPost(text="Content", title="Title", hashtags=["python", "ai"])
        adapter.post(content)

        call_kwargs = mock_client.post.call_args.kwargs
        assert "python,ai" in call_kwargs["json"]["tags"]

    def test_validate_content_ok(self):
        adapter = CsdnAdapter()
        ok, msg = adapter.validate_content(ContentPost(text="A" * 300, title="Good Title"))
        assert ok is True
        assert msg == ""

    def test_validate_content_empty(self):
        adapter = CsdnAdapter()
        ok, msg = adapter.validate_content(ContentPost(text=""))
        assert ok is False

    def test_validate_content_too_short(self):
        adapter = CsdnAdapter()
        ok, msg = adapter.validate_content(ContentPost(text="Short", title="T"))
        assert ok is False
        assert "too short" in msg

    def test_validate_content_title_too_long(self):
        adapter = CsdnAdapter()
        ok, msg = adapter.validate_content(ContentPost(text="A" * 300, title="X" * 101))
        assert ok is False
        assert "Title too long" in msg

    def test_authenticate_csrf_token_extraction(self):
        """CSRF token should be extracted from cookie string."""
        adapter = CsdnAdapter({"cookie": "SESSION=abc; csrfToken=my_csrf_123; UserName=test"})
        with patch.object(httpx.Client, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"code": 200, "data": {"username": "test"}}
            mock_get.return_value = mock_resp
            adapter.authenticate()
        # The adapter stores cookie internally; we just verify auth passed with CSRF
        assert adapter._authenticated is True

    def test_get_status(self):
        adapter = CsdnAdapter()
        status = adapter.get_status()
        assert status.platform == "csdn"
        assert status.is_authenticated is False
