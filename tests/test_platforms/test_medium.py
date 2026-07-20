"""Tests for Medium platform adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from platforms.base import ContentPost
from platforms.medium import MediumAdapter


class TestMediumAdapter:
    def test_initialization(self):
        adapter = MediumAdapter({"api_key": "k"})
        assert adapter.platform_name == "medium"

    def test_authenticate_without_key(self):
        assert MediumAdapter().authenticate() is False

    def test_authenticate_success(self):
        adapter = MediumAdapter({"api_key": "valid"})
        with patch.object(httpx.Client, "get") as mock_get:
            mock_resp = MagicMock(status_code=200)
            mock_resp.json.return_value = {"data": {"id": "user_abc"}}
            mock_get.return_value = mock_resp
            assert adapter.authenticate() is True
            assert adapter._user_id == "user_abc"

    def test_post_not_authenticated(self):
        result = MediumAdapter().post(ContentPost(text="Test"))
        assert result.success is False

    def test_post_success(self):
        adapter = MediumAdapter({"api_key": "k"})
        adapter._authenticated = True
        adapter._user_id = "user_1"
        mock_client = MagicMock()
        mock_client.post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"data": {"id": "post_123", "url": "https://medium.com/post"}},
        )
        adapter._client = mock_client

        result = adapter.post(ContentPost(text="Content", title="Title", hashtags=["python"]))
        assert result.success is True
        assert result.post_id == "post_123"

    def test_validate_content_ok(self):
        adapter = MediumAdapter()
        ok, _ = adapter.validate_content(ContentPost(text="Hello", title="Title"))
        assert ok is True

    def test_get_status(self):
        status = MediumAdapter().get_status()
        assert status.platform == "medium"
