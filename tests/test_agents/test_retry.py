"""Tests for the retry mechanism (exponential backoff)."""

from __future__ import annotations

from unittest.mock import MagicMock

from agents.base import Task, TaskResult
from agents.writer import WriterAgent
from platforms.base import BasePlatformAdapter, ContentPost, PostResult


class TestRetryCount:
    """Verify retry_count field is set correctly."""

    def test_task_result_default_retry_count(self):
        result = TaskResult(task_id="t1", success=True)
        assert result.retry_count == 0

    def test_task_result_retry_count_to_dict(self):
        result = TaskResult(task_id="t1", success=True, retry_count=2)
        d = result.to_dict()
        assert d["retry_count"] == 2

    def test_post_result_default_retry_count(self):
        result = PostResult(success=True, platform="juejin")
        assert result.retry_count == 0


class TestBaseAgentRetry:
    """Test execute_with_retry on BaseAgent."""

    def test_execute_with_retry_succeeds_first_try(self, mock_llm_client):
        """If execute succeeds on first attempt, no retry needed."""
        writer = WriterAgent(mock_llm_client)
        task = Task(
            task_id="t_retry_1",
            task_type="write",
            params={"topic": "Test", "enable_rag": False},
        )
        result = writer.execute_with_retry(task, max_retries=2)
        assert result.success
        assert result.retry_count == 0

    def test_execute_with_retry_eventually_succeeds(self, mock_llm_client):
        """Execute fails once, then succeeds on retry."""

        class FlakyAgent(WriterAgent):
            def __init__(self, client):
                super().__init__(client)
                self.call_count = 0

            def execute(self, task):
                self.call_count += 1
                if self.call_count == 1:
                    return TaskResult(
                        task_id=task.task_id,
                        success=False,
                        error_message="Temporary failure",
                        agent_name=self.name,
                    )
                return super().execute(task)

        agent = FlakyAgent(mock_llm_client)
        task = Task(
            task_id="t_retry_2",
            task_type="write",
            params={"topic": "Test", "enable_rag": False},
        )
        result = agent.execute_with_retry(task, max_retries=3)
        assert result.success
        assert result.retry_count == 1  # Second attempt (zero-indexed)
        assert agent.call_count == 2

    def test_execute_with_retry_exhausted(self, mock_llm_client):
        """All attempts fail → return failed result with retry_count."""
        failing_agent = WriterAgent(mock_llm_client)
        failing_agent.execute = MagicMock(
            return_value=TaskResult(
                task_id="t", success=False, error_message="Dead", agent_name="writer"
            )
        )

        task = Task(task_id="t_retry_3", task_type="write", params={})
        result = failing_agent.execute_with_retry(task, max_retries=2)
        assert not result.success
        assert result.retry_count == 2  # Last attempt
        assert failing_agent.execute.call_count == 3  # 1 initial + 2 retries

    def test_execute_with_retry_exception_handling(self, mock_llm_client):
        """Exceptions are caught and retried."""
        agent = WriterAgent(mock_llm_client)
        agent.execute = MagicMock(side_effect=[Exception("Boom"), Exception("Boom"), None])

        task = Task(task_id="t_retry_4", task_type="write", params={})
        # On 3rd call, MagicMock returns None which will fail,
        # but the exception path handles it
        result = agent.execute_with_retry(task, max_retries=2)
        assert not result.success
        assert result.retry_count == 2

    def test_execute_with_retry_preserves_data(self, mock_llm_client):
        """When retry succeeds, data from successful attempt is preserved."""
        writer = WriterAgent(mock_llm_client)
        task = Task(
            task_id="t_retry_5",
            task_type="write",
            params={"topic": "Python", "style": "technical", "enable_rag": False},
        )
        result = writer.execute_with_retry(task, max_retries=2)
        assert result.success
        assert result.data is not None
        assert result.data["topic"] == "Python"


class TestPlatformAdapterRetry:
    """Test post_with_retry on BasePlatformAdapter."""

    def test_post_with_retry_success_first_try(self):
        """Successful post on first attempt."""
        adapter = _make_adapter(post_result=PostResult(success=True, platform="test"))
        result = adapter.post_with_retry(ContentPost(text="Hello"), max_retries=2)
        assert result.success
        assert result.retry_count == 0

    def test_post_with_retry_eventually_succeeds(self):
        """Post fails once, then succeeds on retry."""
        adapter = _make_adapter(
            post_results=[
                PostResult(success=False, platform="test", error_message="Timeout"),
                PostResult(success=True, platform="test", post_id="123"),
            ]
        )
        result = adapter.post_with_retry(ContentPost(text="Hello"), max_retries=3)
        assert result.success
        assert result.post_id == "123"
        assert result.retry_count == 1

    def test_post_with_retry_exhausted(self):
        """All post attempts fail."""
        adapter = _make_adapter(
            post_results=[
                PostResult(success=False, platform="test", error_message="Err1"),
                PostResult(success=False, platform="test", error_message="Err2"),
                PostResult(success=False, platform="test", error_message="Err3"),
            ]
        )
        result = adapter.post_with_retry(ContentPost(text="Hello"), max_retries=2)
        assert not result.success
        assert result.retry_count >= 2

    def test_post_with_retry_exception(self):
        """Exception thrown during post → retry."""
        adapter = _make_adapter(exception=Exception("Network error"))
        result = adapter.post_with_retry(ContentPost(text="Hello"), max_retries=1)
        assert not result.success
        assert "2 attempts failed" in (result.error_message or "")


class TestRetryUtility:
    """Test the utils/retry module."""

    def test_retry_with_backoff_decorator_success(self):
        from utils import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=2, backoff_base=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Transient")
            return "ok"

        result = flaky_func()
        assert result == "ok"
        assert call_count == 2

    def test_retry_with_backoff_decorator_exhausted(self):
        from utils import retry_with_backoff

        @retry_with_backoff(max_retries=1, backoff_base=0.01)
        def always_fails():
            raise RuntimeError("Always")

        try:
            always_fails()
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "Always" in str(e)

    def test_retry_with_backoff_does_not_retry_success(self):
        from utils import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, backoff_base=0.01)
        def works_first_time():
            nonlocal call_count
            call_count += 1
            return "done"

        result = works_first_time()
        assert result == "done"
        assert call_count == 1

    def test_retry_callable(self):
        from utils import retry_callable

        attempts = 0

        def fn():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ConnectionError("Transient")
            return attempts

        result, attempt = retry_callable(fn, max_retries=2, backoff_base=0.01)
        assert result == 2
        assert attempt == 1


# ── Helpers ────────────────────────────────────────────────────────


def _make_adapter(*, post_result=None, post_results=None, exception=None):
    """Create a minimal adapter with controlled post behavior."""

    call_count = 0

    class TestAdapter(BasePlatformAdapter):
        platform_name = "test"

        def authenticate(self):
            self._authenticated = True
            return True

        def post(self, content):
            nonlocal call_count
            if exception:
                call_count += 1
                raise exception
            if post_results:
                r = post_results[min(call_count, len(post_results) - 1)]
                call_count += 1
                return r
            return post_result or PostResult(success=True, platform="test")

    return TestAdapter()
