"""
MCPServer — wraps AgentCrew ToolRegistry as an MCP server.

Exposes AgentCrew tools to external AI applications (Claude Desktop,
Continue, etc.) via the Model Context Protocol.

Uses the official mcp Python SDK.

Usage:
    from crew_mcp.server import MCPServer
    from crew_mcp.config import MCPServerConfig

    server = MCPServer(tool_registry, config=MCPServerConfig(enabled=True))
    await server.run_stdio()
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.lowlevel.server import Server as McpSdkServer
from mcp.server.stdio import stdio_server
from mcp.types import TextContent
from mcp.types import Tool as McpTool

from agents.tools import ToolRegistry
from crew_mcp.adapter import agentcrew_tool_to_mcp_tool
from crew_mcp.config import MCPServerConfig

logger = logging.getLogger(__name__)


class MCPServer:
    """Expose AgentCrew ToolRegistry tools as an MCP-compatible server.

    Wraps the official mcp.server.Server with automatic tool registration
    from an AgentCrew ToolRegistry. Each AgentCrew Tool becomes an MCP tool
    with its inputSchema derived directly from tool.parameters.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        config: MCPServerConfig | None = None,
    ):
        """Initialize the MCP server.

        Args:
            tool_registry: AgentCrew ToolRegistry with tools to expose.
            config: Server configuration. Uses defaults if None.
        """
        self._tool_registry = tool_registry
        self._config = config or MCPServerConfig()
        self._tool_map: dict[str, Any] = {}  # tool_name -> AgentCrew Tool

        # Create the underlying MCP SDK server
        self._server = McpSdkServer(
            name="agentcrew-mcn",
            version="0.1.0",
            instructions="AgentCrew MCN — AI content marketing automation tools.",
        )

        # Register handlers
        self._register_handlers()

    def _build_mcp_tool_defs(self) -> list[McpTool]:
        """Build the list of MCP tool definitions from the registry.

        Populates self._tool_map as a side effect.
        """
        tools = self._tool_registry.list_tools()
        mcp_tools: list[McpTool] = []
        for tool in tools:
            mcp_def = agentcrew_tool_to_mcp_tool(tool)
            self._tool_map[tool.name] = tool
            mcp_tools.append(
                McpTool(
                    name=mcp_def["name"],
                    description=mcp_def["description"],
                    inputSchema=mcp_def["inputSchema"],
                )
            )
        return mcp_tools

    async def _execute_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute a registered tool by name.

        Args:
            name: Tool name to execute.
            arguments: Keyword arguments to pass to the tool function.

        Returns:
            List of TextContent blocks with the tool result or error message.
        """
        tool = self._tool_map.get(name)
        if tool is None:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Unknown tool '{name}'. "
                    f"Available: {list(self._tool_map.keys())}",
                )
            ]

        try:
            result = tool.execute(**arguments)
            return [TextContent(type="text", text=str(result))]
        except Exception as e:
            logger.error(f"Tool '{name}' execution failed: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"Error executing '{name}': {str(e)}",
                )
            ]

    def _register_handlers(self) -> None:
        """Register list_tools and call_tool handlers on the MCP server."""

        # Pre-build the tool definitions (populates _tool_map as side effect)
        mcp_tools = self._build_mcp_tool_defs()

        @self._server.list_tools()
        async def list_tools() -> list[McpTool]:
            """Return all available MCP tools."""
            return mcp_tools

        @self._server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Execute a tool by name with given arguments."""
            return await self._execute_tool(name, arguments)

    async def run_stdio(self) -> None:
        """Run the MCP server over stdio transport.

        Blocks until stdin closes. Use for integration with
        Claude Desktop, Continue, and other local AI apps.
        """
        logger.info("Starting AgentCrew MCP server over stdio...")
        async with stdio_server() as (read_stream, write_stream):
            init_options = self._server.create_initialization_options()
            await self._server.run(read_stream, write_stream, init_options)

    async def run_sse(self, host: str | None = None, port: int | None = None) -> None:
        """Run the MCP server over SSE (Server-Sent Events) transport.

        Args:
            host: Bind address. Uses config.host if not specified.
            port: Port number. Uses config.port if not specified.
        """
        from mcp.server.sse import SseServerTransport

        host = host or self._config.host
        port = port or self._config.port

        logger.info(f"Starting AgentCrew MCP server over SSE on {host}:{port}...")

        # SSE uses a different transport setup
        transport = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await self._server.run(
                    streams[0],
                    streams[1],
                    self._server.create_initialization_options(),
                )

        import uvicorn
        from starlette.applications import Starlette
        from starlette.routing import Route

        async def sse_endpoint(request):
            return await handle_sse(request)

        app = Starlette(
            routes=[
                Route("/sse", sse_endpoint),
                Route("/messages/", transport.handle_post_message, methods=["POST"]),
            ],
        )

        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
