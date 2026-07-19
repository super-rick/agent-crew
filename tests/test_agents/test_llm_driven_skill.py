"""Tests for LLM-driven skill orchestration (v0.4)."""

from __future__ import annotations

from agents.base import Task
from agents.skills import (
    ResearchAndWriteSkill,
    SkillRegistry,
)
from agents.tools import ToolRegistry


class TestLLMDrivenSkill:
    """Test the LLM-driven skill execution flow."""

    def test_llm_driven_skill_workflow_type(self):
        """LLMDrivenSkill subclasses should have workflow_type='llm_driven'."""
        assert ResearchAndWriteSkill.workflow_type == "llm_driven"
        assert ResearchAndWriteSkill.name == "research_and_write"

    def test_registry_rejects_llm_driven_without_client(self):
        """LLM-driven skill without LLM client should return error."""
        registry = SkillRegistry()
        registry.register(ResearchAndWriteSkill)
        tool_registry = ToolRegistry()

        result = registry.execute("research_and_write", tool_registry, {"topic": "Test"})
        assert not result.success
        assert "LLM client required" in (result.error_message or "")

    def test_registry_executes_llm_driven_with_client(self, mock_llm_client):
        """LLM-driven skill with mock LLM client should succeed."""
        mock_llm_client.chat.return_value = (
            '[{"tool": "get_current_time", "args": {}},'
            '{"tool": "web_search", "args": {"query": "Python AI", "max_results": 3}}]'
        )
        registry = SkillRegistry()
        registry.register(ResearchAndWriteSkill)
        tool_registry = ToolRegistry()
        # Register a mock tool
        from agents.tools import Tool

        tool_registry.register(
            Tool(
                name="web_search",
                description="Search the web",
                parameters={"type": "object", "properties": {}},
                func=lambda **kw: [{"title": "Result", "snippet": "Info"}],
            )
        )
        tool_registry.register(
            Tool(
                name="get_current_time",
                description="Get current time",
                parameters={"type": "object", "properties": {}},
                func=lambda: "2026-07-19 18:00:00",
            )
        )

        result = registry.execute(
            "research_and_write",
            tool_registry,
            {"topic": "Python AI"},
            llm_client=mock_llm_client,
        )
        assert result.success
        assert result.data is not None
        assert "search_context" in result.data

    def test_llm_driven_handles_json_parse_error(self, mock_llm_client):
        """If LLM returns malformed JSON, should handle gracefully."""
        mock_llm_client.chat.return_value = "not valid json at all"
        registry = SkillRegistry()
        registry.register(ResearchAndWriteSkill)
        tool_registry = ToolRegistry()

        from agents.tools import Tool

        tool_registry.register(
            Tool("web_search", "Search", {"type": "object", "properties": {}}, lambda **kw: [])
        )
        tool_registry.register(
            Tool(
                "get_current_time",
                "Time",
                {"type": "object", "properties": {}},
                lambda: "now",
            )
        )

        result = registry.execute(
            "research_and_write",
            tool_registry,
            {"topic": "Test"},
            llm_client=mock_llm_client,
        )
        assert result.success
        assert result.data["search_context"] == "No tools called."

    def test_llm_driven_handles_llm_failure(self, mock_llm_client):
        """If LLM call itself fails, should return error."""
        mock_llm_client.chat.side_effect = Exception("API down")
        registry = SkillRegistry()
        registry.register(ResearchAndWriteSkill)
        tool_registry = ToolRegistry()

        result = registry.execute(
            "research_and_write",
            tool_registry,
            {"topic": "Test"},
            llm_client=mock_llm_client,
        )
        assert not result.success
        assert "API down" in (result.error_message or "")

    def test_llm_driven_with_json_in_markdown(self, mock_llm_client):
        """LLM returns JSON wrapped in markdown code block."""
        mock_llm_client.chat.return_value = (
            "Here's my plan:\n```json\n"
            '[{"tool": "get_current_time", "args": {}},'
            '{"tool": "web_search", "args": {"query": "test"}}]\n```'
        )
        registry = SkillRegistry()
        registry.register(ResearchAndWriteSkill)
        tool_registry = ToolRegistry()

        from agents.tools import Tool

        tool_registry.register(
            Tool("web_search", "Search", {"type": "object", "properties": {}}, lambda **kw: [])
        )
        tool_registry.register(
            Tool(
                "get_current_time",
                "Time",
                {"type": "object", "properties": {}},
                lambda: "now",
            )
        )

        result = registry.execute(
            "research_and_write",
            tool_registry,
            {"topic": "test"},
            llm_client=mock_llm_client,
        )
        assert result.success

    def test_deterministic_skill_still_works(self, mock_llm_client):
        """Existing deterministic skills should not be affected."""
        registry = SkillRegistry()
        from agents.skills import TrendingWritingSkill

        registry.register(TrendingWritingSkill)
        tool_registry = ToolRegistry()

        from agents.tools import Tool

        tool_registry.register(
            Tool(
                "web_search",
                "Search",
                {"type": "object", "properties": {}},
                lambda **kw: [{"title": "Hot", "snippet": "Trending topic"}],
            )
        )
        tool_registry.register(
            Tool(
                "get_current_time",
                "Time",
                {"type": "object", "properties": {}},
                lambda: "2026-07-19",
            )
        )

        result = registry.execute(
            "trending_writing",
            tool_registry,
            {"topic": "AI"},
            llm_client=mock_llm_client,
        )
        assert result.success
        assert result.skill_name == "trending_writing"

    def test_llm_driven_skips_unknown_tools(self, mock_llm_client):
        """If LLM plans an unknown tool, it should be skipped."""
        mock_llm_client.chat.return_value = (
            '[{"tool": "unknown_tool", "args": {}},'
            '{"tool": "web_search", "args": {"query": "Python"}}]'
        )
        registry = SkillRegistry()
        registry.register(ResearchAndWriteSkill)
        tool_registry = ToolRegistry()

        from agents.tools import Tool

        tool_registry.register(
            Tool(
                "web_search",
                "Search",
                {"type": "object", "properties": {}},
                lambda **kw: [{"title": "R", "snippet": "Found"}],
            )
        )

        result = registry.execute(
            "research_and_write",
            tool_registry,
            {"topic": "Python"},
            llm_client=mock_llm_client,
        )
        assert result.success
        # Only web_search was called (unknown tool skipped)
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["tool"] == "web_search"

    def test_llm_driven_logs_tool_errors(self, mock_llm_client):
        """Tool execution errors should be logged, not crash."""
        mock_llm_client.chat.return_value = (
            '[{"tool": "get_current_time", "args": {"bad_arg": true}}]'
        )
        registry = SkillRegistry()
        registry.register(ResearchAndWriteSkill)
        tool_registry = ToolRegistry()

        from agents.tools import Tool

        def failing_tool():
            raise ValueError("Boom")

        tool_registry.register(
            Tool(
                "get_current_time",
                "Time",
                {"type": "object", "properties": {}},
                func=failing_tool,
            )
        )

        result = registry.execute(
            "research_and_write",
            tool_registry,
            {"topic": "Test"},
            llm_client=mock_llm_client,
        )
        assert result.success
        assert any("error" in tc for tc in result.tool_calls)


class TestWriterWithLLMDrivenSkills:
    """Integration: WriterAgent uses LLM-driven skills."""

    def test_writer_uses_research_and_write(self, mock_llm_client):
        """Writer should be able to use the new LLM-driven skill."""
        from agents.writer import WriterAgent

        mock_llm_client.chat.return_value = (
            '[{"tool": "get_current_time", "args": {}},'
            '{"tool": "web_search", "args": {"query": "AI Agent 2026"}}]'
        )
        writer = WriterAgent(mock_llm_client)
        # Verify the LLM-driven skill is registered
        assert "research_and_write" in writer._skill_registry.list_names()

        task = Task(
            task_id="t_llm_skill",
            task_type="write",
            params={
                "topic": "AI Agent",
                "style": "technical",
                "skill": "research_and_write",
                "enable_rag": False,
            },
        )
        result = writer.execute(task)
        assert result.success
        assert result.data["skill_used"] == "research_and_write"


class TestToolRegistryDescribe:
    """Test the new describe_all() method."""

    def test_describe_all(self):
        registry = ToolRegistry()
        from agents.tools import Tool

        registry.register(Tool("t1", "First tool", {"type": "object", "properties": {}}, lambda: 1))
        registry.register(
            Tool("t2", "Second tool", {"type": "object", "properties": {}}, lambda: 2)
        )
        desc = registry.describe_all()
        assert "t1" in desc
        assert "t2" in desc
        assert "First tool" in desc
