"""Tests for async LLM client and agent variants (v0.4 tech debt)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from agents.base import Task, TaskResult
from agents.writer import WriterAgent
from llm.client import LLMClient, LLMConfig


class TestAsyncLLMClient:
    """Test async variants of LLMClient."""

    @patch("openai.OpenAI")
    def test_achat_returns_content(self, mock_openai):
        """achat() should return content string via run_in_executor."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Async response"
        mock_client.chat.completions.create.return_value.choices = [mock_choice]
        mock_openai.return_value = mock_client

        async def run():
            client = LLMClient(LLMConfig(api_key="test"))
            return await client.achat([{"role": "user", "content": "hi"}])

        result = asyncio.run(run())
        assert result == "Async response"

    @patch("openai.OpenAI")
    def test_achat_passes_parameters(self, mock_openai):
        """achat() should pass through temperature and max_tokens."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        mock_client.chat.completions.create.return_value.choices = [mock_choice]
        mock_openai.return_value = mock_client

        async def run():
            client = LLMClient(LLMConfig(api_key="test"))
            return await client.achat(
                [{"role": "user", "content": "x"}],
                temperature=0.3,
                max_tokens=50,
            )

        result = asyncio.run(run())
        assert result == "ok"
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["max_tokens"] == 50

    @patch("openai.OpenAI")
    def test_achat_handles_empty(self, mock_openai):
        """achat() handles None content."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_client.chat.completions.create.return_value.choices = [mock_choice]
        mock_openai.return_value = mock_client

        async def run():
            client = LLMClient(LLMConfig(api_key="test"))
            return await client.achat([{"role": "user", "content": ""}])

        result = asyncio.run(run())
        assert result == ""


class TestAsyncAgent:
    """Test async execute on BaseAgent."""

    def test_aexecute_returns_task_result(self, mock_llm_client):
        """aexecute() should wrap sync execute() and return TaskResult."""

        async def run():
            writer = WriterAgent(mock_llm_client)
            task = Task(
                task_id="t_async",
                task_type="write",
                params={"topic": "Python", "enable_rag": False},
            )
            result = await writer.aexecute(task)
            assert isinstance(result, TaskResult)
            assert result.success
            assert result.data["topic"] == "Python"
            return result

        result = asyncio.run(run())
        assert result.success

    def test_aexecute_runs_concurrently(self, mock_llm_client):
        """Multiple async executes should work concurrently."""

        async def run_one(topic: str):
            writer = WriterAgent(mock_llm_client)
            task = Task(
                task_id=f"t_{topic}",
                task_type="write",
                params={"topic": topic, "enable_rag": False},
            )
            return await writer.aexecute(task)

        async def run_all():
            return await asyncio.gather(
                run_one("Python"),
                run_one("JavaScript"),
                run_one("Rust"),
            )

        results = asyncio.run(run_all())
        assert len(results) == 3
        assert all(r.success for r in results)
        topics = {r.data["topic"] for r in results}
        assert topics == {"Python", "JavaScript", "Rust"}
