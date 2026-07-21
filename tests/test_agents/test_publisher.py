"""Tests for the Publisher Agent."""

from __future__ import annotations

import os
import tempfile

import pytest

from agents.base import Task
from agents.publisher import PublisherAgent
from platforms.base import BasePlatformAdapter, ContentPost, PostResult


@pytest.fixture
def isolated_history_file():
    """Provide a temp history file path, clean up after test."""
    fd, path = tempfile.mkstemp(suffix=".json", prefix="test_pub_hist_")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


class MockPlatform(BasePlatformAdapter):
    """Mock platform adapter for testing."""

    platform_name = "mock_platform"
    rate_limit_per_hour = 100

    def authenticate(self) -> bool:
        self._authenticated = True
        return True

    def post(self, content: ContentPost) -> PostResult:
        return PostResult(
            success=True,
            platform=self.platform_name,
            post_id="mock_123",
            post_url="https://example.com/post/123",
        )


class FailingPlatform(BasePlatformAdapter):
    """Mock platform adapter that fails."""

    platform_name = "failing_platform"

    def authenticate(self) -> bool:
        self._authenticated = True
        return True

    def post(self, content: ContentPost) -> PostResult:
        return PostResult(
            success=False,
            platform=self.platform_name,
            error_message="API returned error",
        )


class TestPublisherAgent:
    """Test suite for PublisherAgent."""

    def test_initialization(self, mock_llm_client):
        pub = PublisherAgent(mock_llm_client)
        assert pub.name == "publisher"
        assert len(pub.list_platforms()) == 0

    def test_register_platform(self, mock_llm_client):
        pub = PublisherAgent(mock_llm_client)
        mock_adapter = MockPlatform()
        pub.register_platform("mock", mock_adapter)
        assert "mock" in pub.list_platforms()
        assert pub.get_platform("mock") == mock_adapter

    def test_execute_dry_run(self, mock_llm_client, isolated_history_file):
        pub = PublisherAgent(mock_llm_client, config={"history_file": isolated_history_file})
        pub.register_platform("mock", MockPlatform())

        task = Task(
            task_id="test_pub_001",
            task_type="publish",
            params={
                "content": {"text": "Hello, world!"},
                "platforms": ["mock"],
                "dry_run": True,
            },
        )
        result = pub.execute(task)
        assert result.success
        assert result.data["dry_run"] is True
        assert result.data["succeeded"] == 1

    def test_execute_real_publish(self, mock_llm_client, isolated_history_file):
        pub = PublisherAgent(mock_llm_client, config={"history_file": isolated_history_file})
        pub.register_platform("mock", MockPlatform())

        task = Task(
            task_id="test_pub_002",
            task_type="publish",
            params={
                "content": {"text": "Hello, world!"},
                "platforms": ["mock"],
                "dry_run": False,
            },
        )
        result = pub.execute(task)
        assert result.success
        assert result.data["succeeded"] == 1

    def test_execute_failing_platform(self, mock_llm_client, isolated_history_file):
        pub = PublisherAgent(mock_llm_client, config={"history_file": isolated_history_file})
        pub.register_platform("failing", FailingPlatform())

        task = Task(
            task_id="test_pub_003",
            task_type="publish",
            params={
                "content": {"text": "Hello"},
                "platforms": ["failing"],
                "dry_run": False,
            },
        )
        result = pub.execute(task)
        assert not result.success

    def test_execute_no_platforms(self, mock_llm_client):
        pub = PublisherAgent(mock_llm_client)
        task = Task(
            task_id="test_pub_004",
            task_type="publish",
            params={"content": {"text": "Hello"}},
        )
        result = pub.execute(task)
        assert not result.success
        assert "No target platforms" in (result.error_message or "")

    def test_execute_invalid_content(self, mock_llm_client):
        pub = PublisherAgent(mock_llm_client)
        task = Task(
            task_id="test_pub_005",
            task_type="publish",
            params={"content": 12345},
        )
        result = pub.execute(task)
        assert not result.success
        assert "Invalid content" in (result.error_message or "")

    def test_content_from_string(self, mock_llm_client, isolated_history_file):
        pub = PublisherAgent(mock_llm_client, config={"history_file": isolated_history_file})
        pub.register_platform("mock", MockPlatform())

        task = Task(
            task_id="test_pub_006",
            task_type="publish",
            params={
                "content": "Simple text content",
                "platforms": ["mock"],
                "dry_run": True,
            },
        )
        result = pub.execute(task)
        assert result.success

    def test_get_platform_not_found(self, mock_llm_client):
        pub = PublisherAgent(mock_llm_client)
        with pytest.raises(KeyError, match="not registered"):
            pub.get_platform("nonexistent")

    def test_post_history(self, mock_llm_client, isolated_history_file):
        pub = PublisherAgent(mock_llm_client, config={"history_file": isolated_history_file})
        pub.register_platform("mock", MockPlatform())

        assert len(pub.get_post_history()) == 0

        # Dry-run should NOT be recorded in history
        dry_task = Task(
            task_id="test_pub_dry",
            task_type="publish",
            params={
                "content": {"text": "Test"},
                "platforms": ["mock"],
                "dry_run": True,
            },
        )
        pub.execute(dry_task)
        assert len(pub.get_post_history()) == 0, "Dry-run should not pollute history"

        # Real publish SHOULD be recorded
        real_task = Task(
            task_id="test_pub_real",
            task_type="publish",
            params={
                "content": {"text": "Test"},
                "platforms": ["mock"],
                "dry_run": False,
            },
        )
        pub.execute(real_task)
        assert len(pub.get_post_history()) == 1, "Real publish should be recorded"
