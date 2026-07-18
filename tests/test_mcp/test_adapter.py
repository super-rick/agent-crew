"""Tests for mcp/adapter.py — bidirectional Tool <-> MCP format conversion."""

from __future__ import annotations

from agents.tools import BUILTIN_TOOLS, ToolRegistry
from crew_mcp.adapter import (
    agentcrew_tool_to_mcp_tool,
    mcp_tool_to_agentcrew_tool,
)

# ============================================================
# agentcrew_tool_to_mcp_tool
# ============================================================


class TestAgentCrewToMCP:
    """AgentCrew Tool -> MCP tool definition conversion."""

    def test_converts_builtin_web_search(self):
        """BUILTIN_TOOLS[0] (web_search) converts correctly."""
        tool = BUILTIN_TOOLS[0]
        assert tool.name == "web_search"

        result = agentcrew_tool_to_mcp_tool(tool)

        assert result["name"] == "web_search"
        assert "搜索" in result["description"]
        assert result["inputSchema"]["type"] == "object"
        assert "query" in result["inputSchema"]["properties"]
        assert "query" in result["inputSchema"]["required"]

    def test_converts_builtin_get_current_time(self):
        """get_current_time (no params) converts correctly."""
        tool = BUILTIN_TOOLS[2]
        assert tool.name == "get_current_time"

        result = agentcrew_tool_to_mcp_tool(tool)

        assert result["name"] == "get_current_time"
        assert result["inputSchema"]["type"] == "object"
        assert result["inputSchema"]["properties"] == {}

    def test_preserves_full_parameters_schema(self, sample_agentcrew_tool):
        """Full parameters JSON Schema is preserved in inputSchema."""
        result = agentcrew_tool_to_mcp_tool(sample_agentcrew_tool)

        schema = result["inputSchema"]
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "limit" in schema["properties"]
        assert schema["properties"]["query"]["type"] == "string"
        assert schema["properties"]["limit"]["type"] == "integer"
        assert schema["properties"]["limit"]["default"] == 10
        assert schema["required"] == ["query"]

    def test_returns_dict_with_three_keys(self, sample_agentcrew_tool):
        """MCP tool definition has exactly: name, description, inputSchema."""
        result = agentcrew_tool_to_mcp_tool(sample_agentcrew_tool)

        assert set(result.keys()) == {"name", "description", "inputSchema"}
        assert isinstance(result["name"], str)
        assert isinstance(result["description"], str)
        assert isinstance(result["inputSchema"], dict)


# ============================================================
# mcp_tool_to_agentcrew_tool
# ============================================================


class TestMCPToAgentCrew:
    """MCP tool definition -> AgentCrew Tool conversion."""

    def test_creates_valid_tool(self, sample_mcp_tool_def):
        """MCP tool def creates a valid AgentCrew Tool."""
        calls = []

        def execute_fn(**kwargs):
            calls.append(kwargs)
            return f"remote result: {kwargs}"

        tool = mcp_tool_to_agentcrew_tool(
            name=sample_mcp_tool_def["name"],
            description=sample_mcp_tool_def["description"],
            input_schema=sample_mcp_tool_def["inputSchema"],
            execute_fn=execute_fn,
        )

        assert tool.name == "remote_search"
        assert tool.description == "A remote search tool from an MCP server"
        assert tool.parameters["type"] == "object"
        assert "query" in tool.parameters["properties"]
        assert "max_results" in tool.parameters["properties"]

    def test_execute_delegates_to_fn(self, sample_mcp_tool_def):
        """Calling tool.execute() delegates to the provided execute_fn."""
        received_kwargs = None

        def execute_fn(**kwargs):
            nonlocal received_kwargs
            received_kwargs = kwargs
            return {"status": "ok", "results": ["a", "b"]}

        tool = mcp_tool_to_agentcrew_tool(
            name=sample_mcp_tool_def["name"],
            description=sample_mcp_tool_def["description"],
            input_schema=sample_mcp_tool_def["inputSchema"],
            execute_fn=execute_fn,
        )

        result = tool.execute(query="test query", max_results=5)

        assert received_kwargs == {"query": "test query", "max_results": 5}
        assert result == {"status": "ok", "results": ["a", "b"]}

    def test_normalizes_missing_type_field(self, sample_mcp_tool_def_no_type):
        """inputSchema without 'type' gets 'type': 'object' added."""
        tool = mcp_tool_to_agentcrew_tool(
            name=sample_mcp_tool_def_no_type["name"],
            description=sample_mcp_tool_def_no_type["description"],
            input_schema=sample_mcp_tool_def_no_type["inputSchema"],
            execute_fn=lambda **kw: kw,
        )

        assert tool.parameters["type"] == "object"
        assert "text" in tool.parameters["properties"]

    def test_normalizes_empty_schema(self, sample_mcp_tool_def_empty):
        """Empty inputSchema gets proper structure."""
        tool = mcp_tool_to_agentcrew_tool(
            name=sample_mcp_tool_def_empty["name"],
            description=sample_mcp_tool_def_empty["description"],
            input_schema=sample_mcp_tool_def_empty["inputSchema"],
            execute_fn=lambda **kw: kw,
        )

        assert tool.parameters["type"] == "object"
        assert tool.parameters["properties"] == {}

    def test_can_register_in_tool_registry(self, sample_mcp_tool_def):
        """Converted tool can be registered and used in ToolRegistry."""
        tool = mcp_tool_to_agentcrew_tool(
            name=sample_mcp_tool_def["name"],
            description=sample_mcp_tool_def["description"],
            input_schema=sample_mcp_tool_def["inputSchema"],
            execute_fn=lambda **kw: f"found: {kw}",
        )

        registry = ToolRegistry()
        registry.register(tool)

        assert "remote_search" in registry
        assert len(registry) == 1

    def test_name_collision_overwrites_in_registry(self, sample_mcp_tool_def):
        """Registering a tool with same name overwrites previous (standard behavior)."""
        tool1 = mcp_tool_to_agentcrew_tool(
            name="shared_name",
            description="First tool",
            input_schema={},
            execute_fn=lambda **kw: "first",
        )
        tool2 = mcp_tool_to_agentcrew_tool(
            name="shared_name",
            description="Second tool",
            input_schema={},
            execute_fn=lambda **kw: "second",
        )

        registry = ToolRegistry()
        registry.register(tool1)
        registry.register(tool2)

        assert len(registry) == 1
        assert registry.get("shared_name").description == "Second tool"


# ============================================================
# Round-trip tests
# ============================================================


class TestRoundTrip:
    """AgentCrew -> MCP -> AgentCrew round-trip conversion."""

    def test_roundtrip_preserves_name_and_description(self, sample_agentcrew_tool):
        """Round-trip preserves tool identity (name, description)."""
        mcp_def = agentcrew_tool_to_mcp_tool(sample_agentcrew_tool)

        def execute_fn(**kwargs):
            return sample_agentcrew_tool.execute(**kwargs)

        reconstructed = mcp_tool_to_agentcrew_tool(
            name=mcp_def["name"],
            description=mcp_def["description"],
            input_schema=mcp_def["inputSchema"],
            execute_fn=execute_fn,
        )

        assert reconstructed.name == sample_agentcrew_tool.name
        assert reconstructed.description == sample_agentcrew_tool.description
        assert reconstructed.parameters == sample_agentcrew_tool.parameters

    def test_roundtrip_execution_works(self, sample_agentcrew_tool):
        """Round-tripped tool executes correctly."""
        mcp_def = agentcrew_tool_to_mcp_tool(sample_agentcrew_tool)

        def execute_fn(**kwargs):
            return sample_agentcrew_tool.execute(**kwargs)

        reconstructed = mcp_tool_to_agentcrew_tool(
            name=mcp_def["name"],
            description=mcp_def["description"],
            input_schema=mcp_def["inputSchema"],
            execute_fn=execute_fn,
        )

        result = reconstructed.execute(query="hello", limit=3)
        assert result == "Searched: hello (limit=3)"

    def test_all_builtin_tools_roundtrip(self):
        """Every BUILTIN_TOOL can round-trip without error."""
        for original in BUILTIN_TOOLS:
            mcp_def = agentcrew_tool_to_mcp_tool(original)

            # Simulate the MCP execute wrapper
            def make_fn(t):
                return lambda **kw: t.execute(**kw)

            reconstructed = mcp_tool_to_agentcrew_tool(
                name=mcp_def["name"],
                description=mcp_def["description"],
                input_schema=mcp_def["inputSchema"],
                execute_fn=make_fn(original),
            )

            assert reconstructed.name == original.name
            assert reconstructed.description == original.description
            assert reconstructed.parameters == original.parameters


# ============================================================
# OpenAI function format compatibility
# ============================================================


class TestOpenAICompatibility:
    """MCP-converted tools must remain OpenAI function-calling compatible."""

    def test_mcp_converted_tool_produces_valid_openai_function(self, sample_mcp_tool_def):
        """A tool from MCP -> AgentCrew must produce valid OpenAI function format."""
        tool = mcp_tool_to_agentcrew_tool(
            name=sample_mcp_tool_def["name"],
            description=sample_mcp_tool_def["description"],
            input_schema=sample_mcp_tool_def["inputSchema"],
            execute_fn=lambda **kw: kw,
        )

        openai_func = tool.to_openai_function()

        assert openai_func["type"] == "function"
        assert openai_func["function"]["name"] == "remote_search"
        assert openai_func["function"]["description"] == sample_mcp_tool_def["description"]
        assert openai_func["function"]["parameters"] == tool.parameters

    def test_can_be_used_in_tool_registry_get_openai_functions(self, sample_mcp_tool_def):
        """MCP tools integrate with ToolRegistry.get_openai_functions()."""
        tool = mcp_tool_to_agentcrew_tool(
            name=sample_mcp_tool_def["name"],
            description=sample_mcp_tool_def["description"],
            input_schema=sample_mcp_tool_def["inputSchema"],
            execute_fn=lambda **kw: kw,
        )

        registry = ToolRegistry()
        registry.register(tool)
        registry.register(BUILTIN_TOOLS[0])  # web_search

        functions = registry.get_openai_functions()
        assert len(functions) == 2
        names = [f["function"]["name"] for f in functions]
        assert "remote_search" in names
        assert "web_search" in names
