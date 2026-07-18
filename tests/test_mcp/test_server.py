"""Tests for crew_mcp/server.py — MCPServer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.tools import Tool, ToolRegistry
from crew_mcp.config import MCPServerConfig
from crew_mcp.server import MCPServer


@pytest.fixture
def simple_registry() -> ToolRegistry:
    """A ToolRegistry with a few test tools."""
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="greet",
            description="Greet someone by name",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name to greet"},
                },
                "required": ["name"],
            },
            func=lambda name: f"Hello, {name}!",
        )
    )
    registry.register(
        Tool(
            name="add",
            description="Add two numbers",
            parameters={
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"},
                },
                "required": ["a", "b"],
            },
            func=lambda a, b: a + b,
        )
    )
    return registry


class TestMCPServerInit:
    """Server initialization tests."""

    def test_creates_server_with_default_config(self, simple_registry):
        """MCPServer initializes with default config."""
        server = MCPServer(simple_registry)
        assert server._config.enabled is False
        assert server._config.transport == "stdio"

    def test_accepts_custom_config(self, simple_registry):
        """MCPServer accepts custom MCPServerConfig."""
        config = MCPServerConfig(enabled=True, transport="sse", port=9000)
        server = MCPServer(simple_registry, config=config)
        assert server._config.enabled is True
        assert server._config.port == 9000

    def test_registers_all_tools_in_tool_map(self, simple_registry):
        """All tools from the registry are in the internal tool map."""
        server = MCPServer(simple_registry)
        assert "greet" in server._tool_map
        assert "add" in server._tool_map
        assert server._tool_map["greet"].name == "greet"
        assert server._tool_map["add"].name == "add"

    def test_empty_registry_works(self):
        """Server with empty registry initializes without error."""
        registry = ToolRegistry()
        server = MCPServer(registry)
        assert len(server._tool_map) == 0


class TestMCPServerBuildToolDefs:
    """Tool definition building tests."""

    def test_builds_mcp_tool_defs(self, simple_registry):
        """_build_mcp_tool_defs returns MCP Tool objects."""
        server = MCPServer(simple_registry)
        # _build_mcp_tool_defs is called in __init__, just verify
        # Reset and call again
        server._tool_map.clear()
        mcp_tools = server._build_mcp_tool_defs()

        assert len(mcp_tools) == 2
        tool_names = [t.name for t in mcp_tools]
        assert "greet" in tool_names
        assert "add" in tool_names

    def test_mcp_tool_definitions_have_correct_format(self, simple_registry):
        """Each MCP tool has name, description, inputSchema."""
        server = MCPServer(simple_registry)
        server._tool_map.clear()
        mcp_tools = server._build_mcp_tool_defs()

        for tool in mcp_tools:
            assert tool.name
            assert tool.description
            assert isinstance(tool.inputSchema, dict)
            assert tool.inputSchema["type"] == "object"

    def test_populates_tool_map(self, simple_registry):
        """_build_mcp_tool_defs populates tool_map."""
        server = MCPServer(simple_registry)
        server._tool_map.clear()
        server._build_mcp_tool_defs()

        assert "greet" in server._tool_map
        assert server._tool_map["greet"].name == "greet"


class TestMCPServerExecuteTool:
    """Tool execution tests via _execute_tool()."""

    @pytest.mark.asyncio
    async def test_execute_tool_returns_text_content(self, simple_registry):
        """_execute_tool returns list of TextContent."""
        server = MCPServer(simple_registry)
        result = await server._execute_tool("greet", {"name": "World"})

        assert len(result) == 1
        assert result[0].text == "Hello, World!"
        assert result[0].type == "text"

    @pytest.mark.asyncio
    async def test_execute_tool_with_numeric_args(self, simple_registry):
        """_execute_tool handles numeric arguments correctly."""
        server = MCPServer(simple_registry)
        result = await server._execute_tool("add", {"a": 3, "b": 4})

        assert result[0].text == "7"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_returns_error(self, simple_registry):
        """Calling an unknown tool returns error message."""
        server = MCPServer(simple_registry)
        result = await server._execute_tool("nonexistent", {})

        assert "Error" in result[0].text
        assert "nonexistent" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_handles_exceptions(self, simple_registry):
        """Tool that raises an exception returns error content."""

        # Register a tool that raises
        def explode():
            raise RuntimeError("Boom!")

        simple_registry.register(
            Tool(
                name="explode",
                description="Always fails",
                parameters={"type": "object", "properties": {}},
                func=explode,
            )
        )

        server = MCPServer(simple_registry)
        result = await server._execute_tool("explode", {})

        assert "Error" in result[0].text
        assert "Boom" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_tool_with_empty_arguments(self, simple_registry):
        """Tool with no required params works with empty dict."""
        # Register a no-arg tool
        simple_registry.register(
            Tool(
                name="ping",
                description="Returns pong",
                parameters={"type": "object", "properties": {}},
                func=lambda: "pong",
            )
        )

        server = MCPServer(simple_registry)
        result = await server._execute_tool("ping", {})
        assert result[0].text == "pong"


@pytest.mark.asyncio
@patch("crew_mcp.server.stdio_server")
class TestMCPServerRun:
    """Transport tests with mocked stdio."""

    async def test_run_stdio_registers_and_runs(self, mock_stdio):
        """run_stdio() calls stdio_server and server.run()."""
        from agents.tools import ToolRegistry

        registry = ToolRegistry()
        registry.register(
            Tool(
                name="hello",
                description="Say hello",
                parameters={"type": "object", "properties": {}},
                func=lambda: "world",
            )
        )

        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

        server = MCPServer(registry)
        # Mock server.run to avoid actual execution
        server._server.run = AsyncMock()
        server._server.create_initialization_options = MagicMock()

        await server.run_stdio()
        server._server.run.assert_called_once()

    async def test_empty_registry_server_runs(self, mock_stdio):
        """Server with empty tool registry can still start."""
        registry = ToolRegistry()

        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

        server = MCPServer(registry)
        server._server.run = AsyncMock()
        server._server.create_initialization_options = MagicMock()

        await server.run_stdio()
        server._server.run.assert_called_once()
