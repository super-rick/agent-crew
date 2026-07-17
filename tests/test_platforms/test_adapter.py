from __future__ import annotations
"""Tests for the platform base and adapters."""

from unittest.mock import MagicMock, patch

import pytest

from platforms.base import BasePlatformAdapter, ContentPost, PostResult, PlatformStatus
from platforms.devto import DevToAdapter


class TestDevToAdapter:
    """Test suite for DevToAdapter."""

    def test_initialization(self):
        adapter = DevToAdapter()
        assert adapter.platform_name == "devto"
        assert adapter.rate_limit_per_hour == 30
        assert adapter.supports_media is False
        assert adapter._authenticated is False

    def test_authentication_without_api_key(self):
        adapter = DevToAdapter()
        assert not adapter.authenticate()

    def test_authentication_success(self):
        adapter = DevToAdapter(config={"api_key": "test-key-123"})
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            adapter._client = mock_client
            # Directly set to test
            adapter._api_key = "test-key-123"
            adapter._authenticated = True
            assert adapter._authenticated

    def test_authentication_failure(self):
        adapter = DevToAdapter(config={"api_key": "bad-key"})
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("httpx.Client") as mock_httpx:
            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = mock_response
            mock_httpx.return_value = mock_client_instance

            result = adapter.authenticate()
            assert not result

    def test_validate_content_empty(self):
        adapter = DevToAdapter()
        is_valid, msg = adapter.validate_content(ContentPost(text=""))
        assert not is_valid

    def test_validate_content_ok(self):
        adapter = DevToAdapter()
        is_valid, msg = adapter.validate_content(ContentPost(text="Hello Dev.to!"))
        assert is_valid

    def test_validate_title_too_long(self):
        adapter = DevToAdapter()
        long_title = "A" * 130
        is_valid, msg = adapter.validate_content(
            ContentPost(text="Body text", title=long_title)
        )
        assert not is_valid
        assert "标题" in msg

    def test_post_without_auth(self):
        adapter = DevToAdapter()
        result = adapter.post(ContentPost(text="Test"))
        assert not result.success
        assert "认证失败" in (result.error_message or "")

    def test_post_success(self):
        adapter = DevToAdapter(config={"api_key": "test-key"})
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 12345,
            "url": "https://dev.to/testuser/my-article-1a2b",
        }

        with patch("httpx.Client") as mock_httpx:
            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = MagicMock(status_code=200)
            mock_client_instance.post.return_value = mock_response
            mock_httpx.return_value = mock_client_instance

            adapter.authenticate()
            result = adapter.post(
                ContentPost(
                    text="# Hello\nThis is a test article.",
                    title="My Test Article",
                    hashtags=["#python", "#AI"],
                )
            )

            assert result.success
            assert result.platform == "devto"
            assert result.post_id == "12345"
            assert "dev.to" in (result.post_url or "")

    def test_post_extracts_tags(self):
        adapter = DevToAdapter(config={"api_key": "test-key"})
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 1, "url": "https://dev.to/test/a"}

        with patch("httpx.Client") as mock_httpx:
            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = MagicMock(status_code=200)
            mock_client_instance.post.return_value = mock_response
            mock_httpx.return_value = mock_client_instance

            adapter.authenticate()

            # Verify tags are correctly extracted
            call_args = None

            def capture_post(*args, **kwargs):
                nonlocal call_args
                call_args = kwargs
                return mock_response

            adapter._client.post = capture_post

            adapter.post(
                ContentPost(
                    text="Content",
                    title="Title",
                    hashtags=["#MachineLearning", "#OpenSource"],
                )
            )

            assert call_args is not None
            tags = call_args["json"]["article"]["tags"]
            assert "machinelearning" in tags
            assert "opensource" in tags

    def test_post_api_error(self):
        adapter = DevToAdapter(config={"api_key": "test-key"})
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"error": "Title has already been taken"}

        with patch("httpx.Client") as mock_httpx:
            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = MagicMock(status_code=200)
            mock_client_instance.post.return_value = mock_response
            mock_httpx.return_value = mock_client_instance

            adapter.authenticate()
            result = adapter.post(
                ContentPost(text="Content", title="Duplicate Title")
            )

            assert not result.success
            assert "Title" in (result.error_message or "")

    def test_get_status(self):
        adapter = DevToAdapter()
        status = adapter.get_status()
        assert status.platform == "devto"
        assert status.is_authenticated is False
        assert status.rate_limit_remaining == 30


class TestBasePlatformAdapter:
    """Test suite for BasePlatformAdapter."""

    def test_default_attributes(self):
        class ConcreteAdapter(BasePlatformAdapter):
            platform_name = "test"
            def authenticate(self): return True
            def post(self, content): return PostResult(success=True, platform="test")

        adapter = ConcreteAdapter()
        assert adapter.platform_name == "test"
        assert adapter.rate_limit_per_hour == 999
        assert adapter.supports_media is False
        assert adapter._authenticated is False

    def test_validate_content_empty(self):
        class ConcreteAdapter(BasePlatformAdapter):
            platform_name = "test"
            def authenticate(self): return True
            def post(self, content): return PostResult(success=True, platform="test")

        adapter = ConcreteAdapter()
        is_valid, msg = adapter.validate_content(ContentPost(text=""))
        assert not is_valid
        assert "empty" in msg

    def test_validate_content_ok(self):
        class ConcreteAdapter(BasePlatformAdapter):
            platform_name = "test"
            def authenticate(self): return True
            def post(self, content): return PostResult(success=True, platform="test")

        adapter = ConcreteAdapter()
        is_valid, msg = adapter.validate_content(ContentPost(text="Valid content"))
        assert is_valid

    def test_get_status(self):
        class ConcreteAdapter(BasePlatformAdapter):
            platform_name = "test_platform"
            def authenticate(self): return True
            def post(self, content): return PostResult(success=True, platform="test_platform")

        adapter = ConcreteAdapter()
        status = adapter.get_status()
        assert status.platform == "test_platform"
        assert status.is_authenticated is False

    def test_config_passed_to_adapter(self):
        class ConcreteAdapter(BasePlatformAdapter):
            platform_name = "config_test"
            def authenticate(self): return True
            def post(self, content): return PostResult(success=True, platform="config_test")

        config = {"key": "value", "cookie": "abc"}
        adapter = ConcreteAdapter(config)
        assert adapter.config["key"] == "value"
        assert adapter.config["cookie"] == "abc"


class TestContentPost:
    """Test suite for ContentPost dataclass."""

    def test_default_creation(self):
        post = ContentPost(text="Hello")
        assert post.text == "Hello"
        assert post.title is None
        assert post.media_urls == []
        assert post.hashtags == []
        assert post.reply_to_id is None
        assert post.scheduled_at is None

    def test_full_creation(self):
        from datetime import datetime, timedelta
        later = datetime.now() + timedelta(hours=1)
        post = ContentPost(
            text="Full post",
            title="Title",
            media_urls=["https://example.com/img.png"],
            hashtags=["#AI", "#OpenSource"],
            reply_to_id="12345",
            scheduled_at=later,
        )
        assert post.text == "Full post"
        assert post.title == "Title"
        assert len(post.media_urls) == 1
        assert len(post.hashtags) == 2
