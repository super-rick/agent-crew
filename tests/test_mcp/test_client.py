"""Tests for crew_mcp/client.py — MCPClientManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from crew_mcp.adapter import mcp_tool_to_agentcrew_tool
from crew_mcp.client import MCPClientManager, MCPConnection
from crew_mcp.config import MCPClientConfig


class TestMCPConnectionConfig:
    """Connection configuration tests."""

    def test_connection_holds_config(self):
        """MCPConnection stores its config."""
        cfg = MCPClientConfig(
            name="test_server",
            command="python",
            args=["-m", "my_mcp"],
        )
        conn = MCPConnection("test_server", cfg)
        assert conn.name == "test_server"
        assert conn.config == cfg
        assert conn.is_connected is False

    def test_is_connected_false_before_connect(self):
        """is_connected is False before connect() is called."""
        cfg = MCPClientConfig(name="test")
        conn = MCPConnection("test", cfg)
        assert conn.is_connected is False
        assert conn.mcp_tools == []


class TestMCPConnectionToolConversion:
    """Converting MCP tools to AgentCrew Tools."""

    def test_to_agentcrew_tools_empty(self):
        """Empty mcp_tools list returns empty AgentCrew tools."""
        cfg = MCPClientConfig(name="empty")
        conn = MCPConnection("empty", cfg)
        tools = conn.to_agentcrew_tools()
        assert tools == []

    def test_single_tool_conversion(self):
        """Single MCP tool converts to AgentCrew Tool."""
        from mcp.types import Tool as McpTool

        cfg = MCPClientConfig(name="single")
        conn = MCPConnection("single", cfg)

        mcp_tool = McpTool(
            name="remote_echo",
            description="Echo back the input",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to echo"},
                },
                "required": ["text"],
            },
        )
        conn._mcp_tools = [mcp_tool]

        tools = conn.to_agentcrew_tools()
        assert len(tools) == 1
        assert tools[0].name == "remote_echo"
        assert tools[0].description == "Echo back the input"
        assert tools[0].parameters["type"] == "object"
        assert "text" in tools[0].parameters["properties"]

    def test_multiple_tool_conversion(self):
        """Multiple MCP tools convert to multiple AgentCrew Tools."""
        from mcp.types import Tool as McpTool

        cfg = MCPClientConfig(name="multi")
        conn = MCPConnection("multi", cfg)

        conn._mcp_tools = [
            McpTool(name="tool_a", description="Tool A", inputSchema={}),
            McpTool(name="tool_b", description="Tool B", inputSchema={}),
            McpTool(name="tool_c", description="Tool C", inputSchema={}),
        ]

        tools = conn.to_agentcrew_tools()
        assert len(tools) == 3
        assert [t.name for t in tools] == ["tool_a", "tool_b", "tool_c"]


class TestMCPClientManagerBasic:
    """MCPClientManager initialization and state."""

    def test_empty_configs(self):
        """Manager with no configs initializes cleanly."""
        manager = MCPClientManager()
        assert manager.connections == {}
        assert manager.get_all_tools() == []

    def test_with_configs_no_connect(self):
        """Configs are stored but not connected until connect_all() is called."""
        configs = [
            MCPClientConfig(name="s1", command="python"),
            MCPClientConfig(name="s2", url="http://localhost/sse"),
        ]
        manager = MCPClientManager(configs)
        assert manager.connections == {}
        assert manager.get_all_tools() == []


@pytest.mark.asyncio
@patch("crew_mcp.client.stdio_client")
@patch("crew_mcp.client.ClientSession")
class TestMCPConnectionConnectStdio:
    """stdio transport connection tests."""

    async def test_connect_stdio_discovers_tools(self, mock_session_cls, mock_stdio):
        """connect() discovers tools from a stdio server."""
        from mcp.types import Tool as McpTool

        # Set up mock stdio transport
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

        # Set up mock session
        mock_session = AsyncMock()
        list_result = MagicMock()
        list_result.tools = [
            McpTool(name="t1", description="Tool 1", inputSchema={}),
            McpTool(name="t2", description="Tool 2", inputSchema={}),
        ]
        mock_session.list_tools = AsyncMock(return_value=list_result)
        mock_session.initialize = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        cfg = MCPClientConfig(
            name="test_stdio",
            command="npx",
            args=["-y", "fake-server"],
        )
        conn = MCPConnection("test_stdio", cfg)

        tools = await conn.connect()
        assert len(tools) == 2
        assert conn.is_connected is True
        mock_session.initialize.assert_called_once()
        mock_session.list_tools.assert_called_once()

    async def test_connect_stdio_missing_command(self, mock_session_cls, mock_stdio):
        """stdio connection without command raises ValueError."""
        cfg = MCPClientConfig(name="bad", transport="stdio")  # no command
        conn = MCPConnection("bad", cfg)

        with pytest.raises(ValueError, match="command"):
            await conn.connect()


@pytest.mark.asyncio
@patch("crew_mcp.client.sse_client")
@patch("crew_mcp.client.ClientSession")
class TestMCPConnectionConnectSSE:
    """SSE transport connection tests."""

    async def test_connect_sse_discovers_tools(self, mock_session_cls, mock_sse):
        """connect() discovers tools from an SSE server."""
        from mcp.types import Tool as McpTool

        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_sse.return_value.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_sse.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        list_result = MagicMock()
        list_result.tools = [
            McpTool(name="remote", description="Remote tool", inputSchema={}),
        ]
        mock_session.list_tools = AsyncMock(return_value=list_result)
        mock_session.initialize = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        cfg = MCPClientConfig(
            name="test_sse",
            transport="sse",
            url="https://example.com/sse",
        )
        conn = MCPConnection("test_sse", cfg)

        tools = await conn.connect()
        assert len(tools) == 1
        assert tools[0].name == "remote"
        assert conn.is_connected is True

    async def test_connect_sse_missing_url(self, mock_session_cls, mock_sse):
        """SSE connection without url raises ValueError."""
        cfg = MCPClientConfig(name="bad", transport="sse")  # no url
        conn = MCPConnection("bad", cfg)

        # The error message contains the config repr
        with pytest.raises(ValueError):
            await conn.connect()

    async def test_disconnect_cleans_up(self, mock_session_cls, mock_sse):
        """disconnect() cleans up session and transport."""
        from mcp.types import Tool as McpTool

        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_sse.return_value.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_sse.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        list_result = MagicMock()
        list_result.tools = [
            McpTool(name="r", description="R", inputSchema={}),
        ]
        mock_session.list_tools = AsyncMock(return_value=list_result)
        mock_session.initialize = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        cfg = MCPClientConfig(
            name="sse_conn",
            transport="sse",
            url="https://example.com/sse",
        )
        conn = MCPConnection("sse_conn", cfg)
        await conn.connect()

        assert conn.is_connected is True

        await conn.disconnect()

        assert conn.is_connected is False
        assert conn.mcp_tools == []


@pytest.mark.asyncio
class TestMCPClientManagerConnect:
    """Manager-level connection orchestration — tests connect_all with
    mocked MCPConnection instances."""

    @patch("crew_mcp.client.MCPConnection")
    async def test_connect_all_multiple_servers(self, mock_conn_cls):
        """Multiple servers are all connected."""
        from mcp.types import Tool as McpTool

        # Each call to MCPConnection(name, cfg) returns a new mock instance
        conn_a = AsyncMock()
        conn_a.name = "server_a"
        conn_a.connect = AsyncMock()
        conn_a.mcp_tools = [McpTool(name="a1", description="A1", inputSchema={})]
        # to_agentcrew_tools needs to return real Tool objects
        from crew_mcp.adapter import mcp_tool_to_agentcrew_tool

        conn_a.to_agentcrew_tools = lambda: [
            mcp_tool_to_agentcrew_tool(
                t.name,
                t.description or "",
                t.inputSchema,
                execute_fn=lambda **kw: f"result from {t.name}",
            )
            for t in conn_a.mcp_tools
        ]

        conn_b = AsyncMock()
        conn_b.name = "server_b"
        conn_b.connect = AsyncMock()
        conn_b.mcp_tools = [McpTool(name="b1", description="B1", inputSchema={})]
        conn_b.to_agentcrew_tools = lambda: [
            mcp_tool_to_agentcrew_tool(
                t.name,
                t.description or "",
                t.inputSchema,
                execute_fn=lambda **kw: f"result from {t.name}",
            )
            for t in conn_b.mcp_tools
        ]

        mock_conn_cls.side_effect = [conn_a, conn_b]
        # mock_conn_cls needs to match both server_a and server_b configs
        # side_effect returns conn_a for first call, conn_b for second

        configs = [
            MCPClientConfig(name="server_a", command="cmd_a"),
            MCPClientConfig(name="server_b", command="cmd_b"),
        ]
        manager = MCPClientManager(configs)

        results = await manager.connect_all()
        assert len(results) == 2
        assert len(manager.connections) == 2
        conn_a.connect.assert_called_once()
        conn_b.connect.assert_called_once()

        all_tools = manager.get_all_tools()
        tool_names = [t.name for t in all_tools]
        assert "a1" in tool_names
        assert "b1" in tool_names

    @patch("crew_mcp.client.MCPConnection")
    async def test_connect_all_handles_failure(self, mock_conn_cls):
        """Failed connection doesn't block other connections."""
        from mcp.types import Tool as McpTool

        # First connection fails
        conn_fail = AsyncMock()
        conn_fail.name = "fail_server"
        conn_fail.connect = AsyncMock(side_effect=ConnectionError("Failed to connect"))

        # Second connection succeeds
        conn_ok = AsyncMock()
        conn_ok.name = "ok_server"
        conn_ok.connect = AsyncMock()
        conn_ok.mcp_tools = [McpTool(name="ok_tool", description="OK", inputSchema={})]
        conn_ok.to_agentcrew_tools = lambda: [
            mcp_tool_to_agentcrew_tool(
                t.name,
                t.description or "",
                t.inputSchema,
                execute_fn=lambda **kw: "ok",
            )
            for t in conn_ok.mcp_tools
        ]

        mock_conn_cls.side_effect = [conn_fail, conn_ok]

        configs = [
            MCPClientConfig(name="fail_server", command="bad"),
            MCPClientConfig(name="ok_server", command="good"),
        ]
        manager = MCPClientManager(configs)

        results = await manager.connect_all()
        assert results["fail_server"] == []
        assert len(results["ok_server"]) == 1
        assert len(manager.connections) == 1  # only ok_server connected

    @patch("crew_mcp.client.MCPConnection")
    async def test_disconnect_all_cleans_up(self, mock_conn_cls):
        """disconnect_all() closes all connections."""
        from mcp.types import Tool as McpTool

        conn = AsyncMock()
        conn.name = "s1"
        conn.connect = AsyncMock()
        conn.disconnect = AsyncMock()
        conn.mcp_tools = [McpTool(name="t", description="T", inputSchema={})]
        conn.to_agentcrew_tools = lambda: [
            mcp_tool_to_agentcrew_tool(
                t.name,
                t.description or "",
                t.inputSchema,
                execute_fn=lambda **kw: "tool",
            )
            for t in conn.mcp_tools
        ]

        mock_conn_cls.return_value = conn

        configs = [MCPClientConfig(name="s1", command="cmd")]
        manager = MCPClientManager(configs)
        await manager.connect_all()

        assert len(manager.connections) == 1

        await manager.disconnect_all()
        assert len(manager.connections) == 0
