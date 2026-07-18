"""Tests for the Writer Agent."""

from __future__ import annotations

from unittest.mock import MagicMock

from agents.base import Task
from agents.writer import WriterAgent


class TestWriterAgent:
    """Test suite for WriterAgent."""

    def test_initialization(self, mock_llm_client):
        writer = WriterAgent(mock_llm_client)
        assert writer.name == "writer"
        assert writer.description is not None
        assert len(writer._tool_registry) > 0
        assert len(writer._skill_registry.list_names()) > 0
        assert "trending_writing" in writer._skill_registry.list_names()

    def test_get_system_prompt(self, mock_llm_client):
        writer = WriterAgent(mock_llm_client)
        prompt = writer.get_system_prompt()
        assert prompt is not None
        assert len(prompt) > 0

    def test_execute_basic(self, mock_llm_client):
        writer = WriterAgent(mock_llm_client)
        task = Task(
            task_id="test_w_001",
            task_type="write",
            params={
                "topic": "Python异步编程",
                "style": "technical",
                "platform": "juejin",
                "enable_rag": False,
            },
        )
        result = writer.execute(task)
        assert result.success
        assert result.agent_name == "writer"
        assert result.data["topic"] == "Python异步编程"
        assert result.data["style"] == "technical"
        assert result.data["raw_content"] is not None
        assert result.data["formatted_content"] is not None
        assert result.duration_seconds > 0

    def test_execute_with_skill(self, mock_llm_client):
        writer = WriterAgent(mock_llm_client)
        task = Task(
            task_id="test_w_002",
            task_type="write",
            params={
                "topic": "AI Agent",
                "style": "technical",
                "skill": "trending_writing",
                "enable_rag": False,
            },
        )
        result = writer.execute(task)
        assert result.success
        assert result.data["skill_used"] == "trending_writing"

    def test_generate_outline(self, mock_llm_client):
        writer = WriterAgent(mock_llm_client)
        outline = writer.generate_outline("Python", "technical")
        assert outline is not None
        assert len(outline) > 0

    def test_compose_article(self, mock_llm_client):
        writer = WriterAgent(mock_llm_client)
        content = writer.compose_article("Python", "technical", "juejin", enable_rag=False)
        assert content is not None
        assert "测试生成" in content

    def test_format_for_platform(self, mock_llm_client):
        writer = WriterAgent(mock_llm_client)
        content = "Line 1\n\nLine 2\n\nLine 3"

        # Twitter -> Thread format
        twitter_fmt = writer.format_for_platform(content, "twitter")
        assert "🧵" in twitter_fmt

        # Generic -> no change
        generic_fmt = writer.format_for_platform(content, "generic")
        assert generic_fmt == content

    def test_execute_failure_reported(self):
        """If LLM client throws, the writer should capture it."""
        failing_client = MagicMock()
        failing_client.chat.side_effect = Exception("API Error")

        writer = WriterAgent(failing_client)
        task = Task(
            task_id="test_w_fail",
            task_type="write",
            params={"topic": "Test", "enable_rag": False},
        )

        result = writer.execute(task)
        assert not result.success
        assert "API Error" in (result.error_message or "")
