"""MCP (Model Context Protocol) module for AgentCrew MCN.

Provides bidirectional MCP integration:
- MCPServer: Expose AgentCrew tools to external AI apps (Claude Desktop, etc.)
- MCPClientManager: Connect external MCP servers into AgentCrew agents
- ToolAdapter: Bidirectional format conversion between AgentCrew Tool <> MCP tool

Note: This module is named 'crew_mcp' to avoid collision with the
official 'mcp' Python SDK package (which it depends on).

Usage:
    # Server: expose tools
    from crew_mcp.server import MCPServer
    server = MCPServer(tool_registry, config=MCPServerConfig())
    await server.run_stdio()

    # Client: connect external tools
    from crew_mcp.client import MCPClientManager
    manager = MCPClientManager(client_configs)
    tools = manager.connect_all_sync()
"""

__all__ = ["MCPServer", "MCPClientManager", "MCPConnection"]

from crew_mcp.adapter import (  # noqa: F401 (re-export)
    agentcrew_tool_to_mcp_tool,
    mcp_tool_to_agentcrew_tool,
)

# Server/client are imported lazily — they depend on the MCP SDK
# which may not be installed in all environments.
