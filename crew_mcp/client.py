"""
MCPClientManager — connects AgentCrew to external MCP servers.

Discovers tools from external MCP servers and converts them to AgentCrew
Tool objects that can be registered in ToolRegistry and used transparently
by Skills and Agents.

Usage:
    from crew_mcp.client import MCPClientManager
    from crew_mcp.config import MCPClientConfig

    configs = [MCPClientConfig(name="filesystem", command="npx", ...)]
    manager = MCPClientManager(configs)
    tools = manager.connect_all_sync()
    for tool in tools:
        tool_registry.register(tool)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import Tool as McpTool

from agents.tools import Tool
from crew_mcp.adapter import mcp_tool_to_agentcrew_tool
from crew_mcp.config import MCPClientConfig

logger = logging.getLogger(__name__)


class MCPConnection:
    """Internal: holds a single MCP server connection and its discovered tools.

    Tracks the session and discovered tool definitions for one external
    MCP server. Can be disconnected to clean up resources.
    """

    def __init__(self, name: str, config: MCPClientConfig):
        self.name = name
        self.config = config
        self._session: ClientSession | None = None
        self._context_managers: list[Any] = []  # Keep alive for session lifetime
        self._mcp_tools: list[McpTool] = []  # Raw MCP tool defs from list_tools

    @property
    def is_connected(self) -> bool:
        return self._session is not None

    @property
    def mcp_tools(self) -> list[McpTool]:
        return self._mcp_tools

    def to_agentcrew_tools(self) -> list[Tool]:
        """Convert all discovered MCP tools to AgentCrew Tool objects.

        Each Tool.func wraps the async MCP session.call_tool() via asyncio.run().
        """
        tools: list[Tool] = []
        for mcp_tool in self._mcp_tools:
            execute_fn = self._create_execute_fn(mcp_tool.name)
            tool = mcp_tool_to_agentcrew_tool(
                name=mcp_tool.name,
                description=mcp_tool.description or "",
                input_schema=mcp_tool.inputSchema,
                execute_fn=execute_fn,
            )
            tools.append(tool)
        return tools

    def _create_execute_fn(self, tool_name: str) -> Callable[..., Any]:
        """Create a synchronous execute function that bridges to async MCP call.

        Uses asyncio.run() to execute the async call_tool in a new event loop.
        This is acceptable because tool calls happen a few times per pipeline
        execution, not in a hot loop.
        """

        def execute_fn(**kwargs: Any) -> Any:
            async def _call() -> Any:
                if not self._session:
                    raise RuntimeError(f"MCP connection '{self.name}' is not connected")
                result = await self._session.call_tool(tool_name, arguments=kwargs)
                # Extract text content from the result
                if result.content:
                    return "".join(c.text for c in result.content if hasattr(c, "text"))
                return str(result)

            try:
                asyncio.get_running_loop()
                # We're inside an async context — use a thread-safe approach
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _call())
                    return future.result()
            except RuntimeError:
                # No running loop — safe to use asyncio.run()
                return asyncio.run(_call())

        return execute_fn

    async def connect(self) -> list[McpTool]:
        """Connect to the MCP server and discover tools.

        Returns:
            List of discovered MCP tool definitions.
        """
        if self.config.transport == "stdio":
            return await self._connect_stdio()
        elif self.config.transport == "sse":
            return await self._connect_sse()
        else:
            raise ValueError(
                f"Unsupported transport '{self.config.transport}' for '{self.name}'. "
                f"Use 'stdio' or 'sse'."
            )

    async def _connect_stdio(self) -> list[McpTool]:
        """Connect via stdio transport."""
        if not self.config.command:
            raise ValueError(f"stdio transport requires 'command' for '{self.name}'")

        params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=self.config.env if self.config.env else None,
        )

        # Open stdio transport
        stdio_ctx = stdio_client(params)
        read_stream, write_stream = await stdio_ctx.__aenter__()
        self._context_managers.append((stdio_ctx, read_stream, write_stream))

        # Create and initialize session
        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        self._context_managers.append(session)

        await session.initialize()
        self._session = session

        # Discover tools
        result = await session.list_tools()
        self._mcp_tools = list(result.tools)
        logger.info(
            "Connected to MCP server '%s' via stdio: %d tools discovered",
            self.name,
            len(self._mcp_tools),
        )
        return self._mcp_tools

    async def _connect_sse(self) -> list[McpTool]:
        """Connect via SSE transport."""
        if not self.config.url:
            raise ValueError(f"SSE transport requires 'url' for '{self.config}'")

        sse_ctx = sse_client(
            url=self.config.url,
            headers=self.config.headers if self.config.headers else None,
        )
        read_stream, write_stream = await sse_ctx.__aenter__()
        self._context_managers.append((sse_ctx, read_stream, write_stream))

        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        self._context_managers.append(session)

        await session.initialize()
        self._session = session

        result = await session.list_tools()
        self._mcp_tools = list(result.tools)
        logger.info(
            "Connected to MCP server '%s' via SSE: %d tools discovered",
            self.name,
            len(self._mcp_tools),
        )
        return self._mcp_tools

    async def disconnect(self) -> None:
        """Close the connection and clean up resources."""
        # Close in reverse order (session first, then transport)
        for ctx in reversed(self._context_managers):
            try:
                if hasattr(ctx, "__aexit__"):
                    await ctx.__aexit__(None, None, None)
                elif isinstance(ctx, tuple):
                    # (context_manager, ...) tuple from __aenter__
                    cm = ctx[0]
                    if hasattr(cm, "__aexit__"):
                        await cm.__aexit__(None, None, None)
            except Exception as e:
                logger.debug("Error during disconnect from '%s': %s", self.name, e)

        self._context_managers.clear()
        self._session = None
        self._mcp_tools = []
        logger.info("Disconnected from MCP server '%s'", self.name)


class MCPClientManager:
    """Manages connections to multiple external MCP servers.

    Connects to configured servers, discovers their tools, and provides
    them as AgentCrew Tool objects ready for registration.

    Usage:
        configs = [MCPClientConfig(name="filesystem", ...)]
        manager = MCPClientManager(configs)

        # Async:
        await manager.connect_all()
        tools = manager.get_all_tools()

        # Sync (convenience):
        tools = manager.connect_all_sync()
    """

    def __init__(self, client_configs: list[MCPClientConfig] | None = None):
        self._configs = client_configs or []
        self._connections: dict[str, MCPConnection] = {}

    @property
    def connections(self) -> dict[str, MCPConnection]:
        return self._connections

    def get_all_tools(self) -> list[Tool]:
        """Return all discovered MCP tools as AgentCrew Tool objects.

        Already-connected tools are returned. Call connect_all() first.

        Returns:
            List of AgentCrew Tools wrapping MCP server tools.
        """
        tools: list[Tool] = []
        for conn in self._connections.values():
            tools.extend(conn.to_agentcrew_tools())
        return tools

    async def connect_all(self) -> dict[str, list[Tool]]:
        """Connect to all configured MCP servers and discover their tools.

        Returns:
            Dict mapping connection name -> list of AgentCrew Tools.
        """
        results: dict[str, list[Tool]] = {}
        for cfg in self._configs:
            try:
                conn = MCPConnection(cfg.name, cfg)
                await conn.connect()
                self._connections[cfg.name] = conn
                results[cfg.name] = conn.to_agentcrew_tools()
            except Exception as e:
                logger.warning("Failed to connect to MCP server '%s': %s", cfg.name, e)
                # Continue with other connections
                results[cfg.name] = []
        return results

    def connect_all_sync(self) -> list[Tool]:
        """Synchronous wrapper: connect to all MCP servers.

        Uses asyncio.run() to execute the async connect_all().

        Returns:
            Flat list of all discovered AgentCrew Tools.
        """
        results = asyncio.run(self.connect_all())
        flat: list[Tool] = []
        for tools in results.values():
            flat.extend(tools)
        logger.info(
            "MCP client sync init complete: %d servers, %d tools",
            len(self._connections),
            len(flat),
        )
        return flat

    async def disconnect_all(self) -> None:
        """Close all MCP connections and clean up."""
        for name, conn in list(self._connections.items()):
            try:
                await conn.disconnect()
            except Exception as e:
                logger.debug("Error disconnecting '%s': %s", name, e)
        self._connections.clear()
