"""Tests for the Tool system."""

from __future__ import annotations

import pytest

from agents.tools import BUILTIN_TOOLS, Tool, ToolRegistry


class TestTool:
    """Test suite for Tool class."""

    def test_tool_creation(self):
        def dummy_func():
            return "done"

        tool = Tool(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            func=dummy_func,
        )
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.execute() == "done"

    def test_to_openai_function(self):
        tool = BUILTIN_TOOLS[0]
        func = tool.to_openai_function()
        assert func["type"] == "function"
        assert "function" in func
        assert func["function"]["name"] == tool.name

    def test_get_current_time_tool(self):
        """The get_current_time tool should return a valid time string."""
        tool = None
        for t in BUILTIN_TOOLS:
            if t.name == "get_current_time":
                tool = t
                break
        assert tool is not None
        result = tool.execute()
        assert "T" in result  # ISO format contains T


class TestToolRegistry:
    """Test suite for ToolRegistry."""

    def test_register_and_get(self):
        registry = ToolRegistry()

        def dummy():
            return "ok"

        tool = Tool(name="dummy", description="Dummy", parameters={}, func=dummy)
        registry.register(tool)
        assert registry.get("dummy") == tool

    def test_get_missing_tool(self):
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")

    def test_list_tools(self):
        registry = ToolRegistry()
        for tool in BUILTIN_TOOLS:
            registry.register(tool)
        assert len(registry.list_tools()) == len(BUILTIN_TOOLS)

    def test_list_names(self):
        registry = ToolRegistry()
        for tool in BUILTIN_TOOLS:
            registry.register(tool)
        names = registry.list_names()
        assert "web_search" in names
        assert "get_current_time" in names

    def test_execute(self):
        registry = ToolRegistry()
        for tool in BUILTIN_TOOLS:
            registry.register(tool)
        result = registry.execute("get_current_time")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains(self):
        registry = ToolRegistry()

        def dummy():
            pass

        registry.register(Tool(name="exists", description="", parameters={}, func=dummy))
        assert "exists" in registry
        assert "missing" not in registry

    def test_len(self):
        registry = ToolRegistry()
        for tool in BUILTIN_TOOLS:
            registry.register(tool)
        assert len(registry) == len(BUILTIN_TOOLS)
