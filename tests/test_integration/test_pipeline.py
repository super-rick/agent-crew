"""Integration tests — end-to-end pipeline verification."""

from __future__ import annotations

from agents.publisher import PublisherAgent
from agents.writer import WriterAgent
from orchestrator.manager import Orchestrator


class TestPipeline:
    """End-to-end pipeline integration tests."""

    def test_write_only_pipeline(self, mock_llm_client):
        """Test 'write' task type through orchestrator."""
        writer = WriterAgent(mock_llm_client)
        publisher = PublisherAgent(mock_llm_client)

        orchestrator = Orchestrator()
        orchestrator.register_agent(writer)
        orchestrator.register_agent(publisher)

        task = orchestrator.create_task(
            task_type="write",
            params={"topic": "测试话题", "style": "technical", "enable_rag": False},
        )
        result = orchestrator.execute_pipeline(task)

        assert result.success
        assert result.task_type == "write"
        assert "writer" in result.results
        assert result.results["writer"].success

    def test_publish_dry_run_pipeline(self, mock_llm_client):
        """Test 'publish' dry-run through orchestrator."""
        from platforms.base import BasePlatformAdapter, PostResult

        class MockPlatform(BasePlatformAdapter):
            platform_name = "mock_test"

            def authenticate(self):
                return True

            def post(self, content):
                return PostResult(success=True, platform="mock_test", post_id="1")

        writer = WriterAgent(mock_llm_client)
        publisher = PublisherAgent(mock_llm_client)
        publisher.register_platform("mock_test", MockPlatform())

        orchestrator = Orchestrator()
        orchestrator.register_agent(writer)
        orchestrator.register_agent(publisher)

        task = orchestrator.create_task(
            task_type="publish",
            params={
                "content": {"text": "Test content"},
                "platforms": ["mock_test"],
                "dry_run": True,
            },
        )
        result = orchestrator.execute_pipeline(task)

        assert result.success
        assert "publisher" in result.results

    def test_write_and_publish_pipeline(self, mock_llm_client):
        """Test full 'write_and_publish' pipeline."""
        from platforms.base import BasePlatformAdapter, PostResult

        class MockPlatform(BasePlatformAdapter):
            platform_name = "mock_test"

            def authenticate(self):
                return True

            def post(self, content):
                return PostResult(success=True, platform="mock_test", post_id="1")

        writer = WriterAgent(mock_llm_client)
        publisher = PublisherAgent(mock_llm_client)
        publisher.register_platform("mock_test", MockPlatform())

        orchestrator = Orchestrator()
        orchestrator.register_agent(writer)
        orchestrator.register_agent(publisher)

        task = orchestrator.create_task(
            task_type="write_and_publish",
            params={
                "topic": "测试话题",
                "style": "technical",
                "platforms": ["mock_test"],
                "dry_run": True,
                "enable_rag": False,
            },
        )
        result = orchestrator.execute_pipeline(task)

        assert result.success
        assert "writer" in result.results
        assert "publisher" in result.results
        assert result.results["writer"].success
        assert result.results["publisher"].success

    def test_history_tracking(self, mock_llm_client):
        """Verify pipeline history is tracked."""
        writer = WriterAgent(mock_llm_client)
        publisher = PublisherAgent(mock_llm_client)

        orchestrator = Orchestrator()
        orchestrator.register_agent(writer)
        orchestrator.register_agent(publisher)

        assert len(orchestrator.get_history()) == 0

        task = orchestrator.create_task(
            task_type="write",
            params={"topic": "Test", "enable_rag": False},
        )
        orchestrator.execute_pipeline(task)

        assert len(orchestrator.get_history()) == 1
        assert orchestrator.get_history()[0].success

    def test_missing_agent(self, mock_llm_client):
        """Test behavior when required agent is missing."""
        orchestrator = Orchestrator()
        # Don't register any agents

        task = orchestrator.create_task(task_type="write", params={})
        result = orchestrator.execute_pipeline(task)

        assert not result.success
        assert "not registered" in (result.error_message or "")

    def test_write_review_publish_pipeline(self, mock_llm_client):
        """Test full write_review_publish pipeline flow."""
        from agents.reviewer import ReviewerAgent
        from platforms.base import BasePlatformAdapter, PostResult

        class MockPlatform(BasePlatformAdapter):
            platform_name = "mock"

            def authenticate(self):
                return True

            def post(self, content):
                return PostResult(success=True, platform="mock", post_id="1")

        # Use custom client that returns longer content to pass review
        long_client = __import__("unittest").mock.MagicMock()
        long_client.chat.return_value = "A" * 500 + "\n\n## Title\n\n" + "B" * 500

        writer = WriterAgent(long_client)
        reviewer = ReviewerAgent(mock_llm_client, config={"reviewer_min_score": 10})
        publisher = PublisherAgent(mock_llm_client)
        publisher.register_platform("mock", MockPlatform())

        orchestrator = Orchestrator()
        orchestrator.register_agent(writer)
        orchestrator.register_agent(reviewer)
        orchestrator.register_agent(publisher)

        task = orchestrator.create_task(
            task_type="write_review_publish",
            params={
                "topic": "Python Programming Guide",
                "style": "technical",
                "platform": "generic",
                "platforms": ["mock"],
                "dry_run": True,
                "enable_rag": False,
            },
        )
        result = orchestrator.execute_pipeline(task)

        # Reviewer verifies content, all 3 agents participate
        assert "writer" in result.results
        assert "reviewer" in result.results
        assert "publisher" in result.results

    def test_write_review_publish_reviewer_blocks(self, mock_llm_client):
        """When reviewer blocks, publisher should be skipped."""
        from agents.reviewer import ReviewerAgent

        writer = WriterAgent(mock_llm_client)
        # Create reviewer with strict settings that will fail
        reviewer = ReviewerAgent(
            mock_llm_client,
            config={"reviewer_min_score": 100, "reviewer_sensitive_words": {}},
        )
        publisher = PublisherAgent(mock_llm_client)

        orchestrator = Orchestrator()
        orchestrator.register_agent(writer)
        orchestrator.register_agent(reviewer)
        orchestrator.register_agent(publisher)

        task = orchestrator.create_task(
            task_type="write_review_publish",
            params={
                "topic": "X",
                "style": "technical",
                "platform": "generic",
                "platforms": [],
                "enable_rag": False,
            },
        )
        result = orchestrator.execute_pipeline(task)

        assert not result.success
        pub_result = result.results.get("publisher")
        assert pub_result is not None
        assert not pub_result.success

    def test_review_standalone(self, mock_llm_client):
        """Test standalone review task."""
        from agents.reviewer import ReviewerAgent

        reviewer = ReviewerAgent(mock_llm_client)
        orchestrator = Orchestrator()
        orchestrator.register_agent(reviewer)

        task = orchestrator.create_task(
            task_type="review",
            params={
                "content": {
                    "title": "Good Title Here",
                    "text": "Good content with enough length " * 20,
                },
                "platform": "generic",
                "min_pass_score": 10,
            },
        )
        result = orchestrator.execute_pipeline(task)
        assert result.success
        assert "reviewer" in result.results

    def test_write_and_publish_writer_failure(self, mock_llm_client):
        """When writer fails, publisher should be skipped."""
        writer = WriterAgent(mock_llm_client)
        # Make writer fail
        writer.execute = lambda task: __import__("agents.base").base.TaskResult(
            task_id=task.task_id,
            success=False,
            error_message="Writer failed",
            agent_name="writer",
        )
        publisher = PublisherAgent(mock_llm_client)

        orchestrator = Orchestrator()
        orchestrator.register_agent(writer)
        orchestrator.register_agent(publisher)

        task = orchestrator.create_task(
            task_type="write_and_publish",
            params={"topic": "Test", "enable_rag": False},
        )
        result = orchestrator.execute_pipeline(task)
        assert not result.success
        assert "Skipped" in (result.results["publisher"].error_message or "")
