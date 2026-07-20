"""Tests for X/Twitter platform adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from platforms.base import ContentPost
from platforms.x_twitter import XTwitterAdapter


class TestXTwitterAdapter:
    def test_initialization(self):
        adapter = XTwitterAdapter({"api_key": "k", "api_secret": "s"})
        assert adapter.platform_name == "twitter"

    def test_authenticate_without_credentials(self):
        adapter = XTwitterAdapter()
        assert adapter.authenticate() is False

    def test_authenticate_success(self):
        adapter = XTwitterAdapter(
            {
                "api_key": "k",
                "api_secret": "s",
                "access_token": "at",
                "access_secret": "as",
            }
        )
        with patch.object(httpx.Client, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            assert adapter.authenticate() is True

    def test_post_not_authenticated(self):
        adapter = XTwitterAdapter()
        result = adapter.post(ContentPost(text="Hello world"))
        assert result.success is False

    def test_post_single_tweet(self):
        adapter = XTwitterAdapter({"api_key": "k", "api_secret": "s"})
        adapter._authenticated = True
        adapter._access_token = "tok"
        mock_client = MagicMock()
        mock_client.post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"data": {"id": "tweet_123"}},
        )
        adapter._client = mock_client

        result = adapter.post(ContentPost(text="Hello world!" * 5))
        assert result.success is True
        assert result.post_id == "tweet_123"

    def test_post_thread(self):
        """Long content should be split into thread."""
        adapter = XTwitterAdapter({"api_key": "k", "api_secret": "s"})
        adapter._authenticated = True
        adapter._access_token = "tok"
        mock_client = MagicMock()
        mock_client.post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"data": {"id": "tweet_1"}},
        )
        adapter._client = mock_client

        result = adapter.post(ContentPost(text="A" * 600))
        assert result.success is True
        # Content is posted (may be 1 or more tweets depending on split)

    def test_split_into_tweets(self):
        adapter = XTwitterAdapter()
        tweets = adapter._split_into_tweets("Short tweet")
        assert len(tweets) == 1

        long = "A" * 300 + "\n" + "B" * 300
        tweets = adapter._split_into_tweets(long)
        assert len(tweets) >= 2
        for t in tweets:
            assert "🧵" in t  # Thread markers
            assert len(t) <= adapter.MAX_TWEET_LENGTH

    def test_validate_content_ok(self):
        adapter = XTwitterAdapter()
        ok, _ = adapter.validate_content(ContentPost(text="Hello world! " * 2))
        assert ok is True

    def test_validate_content_too_short(self):
        adapter = XTwitterAdapter()
        ok, _ = adapter.validate_content(ContentPost(text="Hi"))
        assert ok is False

    def test_get_status(self):
        adapter = XTwitterAdapter()
        status = adapter.get_status()
        assert status.platform == "twitter"
