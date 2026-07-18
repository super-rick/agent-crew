"""Tests for the Skill system."""

from __future__ import annotations

import pytest

from agents.skills import BUILTIN_SKILLS, SkillRegistry, TrendingWritingSkill
from agents.tools import BUILTIN_TOOLS, ToolRegistry


class TestSkillRegistry:
    """Test suite for SkillRegistry."""

    def test_register_and_get(self):
        registry = SkillRegistry()
        for skill_class in BUILTIN_SKILLS:
            registry.register(skill_class)
        skill = registry.get("trending_writing")
        assert skill is not None
        assert isinstance(skill, TrendingWritingSkill)

    def test_get_missing_skill(self):
        registry = SkillRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_list_names(self):
        registry = SkillRegistry()
        for skill_class in BUILTIN_SKILLS:
            registry.register(skill_class)
        names = registry.list_names()
        assert "trending_writing" in names
        assert "technical_article" in names
        assert "thread_writing" in names

    def test_execute_trending_writing(self):
        registry = SkillRegistry()
        registry.register(TrendingWritingSkill)

        tool_registry = ToolRegistry()
        for tool in BUILTIN_TOOLS:
            tool_registry.register(tool)

        result = registry.execute(
            "trending_writing",
            tool_registry,
            {"topic": "Python", "style": "technical"},
        )

        assert result.success
        assert result.skill_name == "trending_writing"
        assert result.data["topic"] == "Python"
        assert result.data["current_time"] is not None
        assert "web_search" in [tc["tool"] for tc in result.tool_calls]

    def test_execute_missing_tool(self):
        registry = SkillRegistry()
        registry.register(TrendingWritingSkill)

        empty_registry = ToolRegistry()
        result = registry.execute(
            "trending_writing",
            empty_registry,
            {"topic": "Python"},
        )

        assert not result.success
        assert "Required tool" in (result.error_message or "")
