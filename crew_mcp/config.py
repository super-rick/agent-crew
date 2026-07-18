"""MCP configuration dataclasses and YAML parsing."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MCPServerConfig:
    """Configuration for the MCP Server (exposing AgentCrew tools).

    Attributes:
        enabled: Whether to start the MCP server.
        transport: Transport mechanism — 'stdio' or 'sse'.
        host: Host to bind SSE server (default: 127.0.0.1).
        port: Port for SSE server (default: 8090).
        expose_skills: Future: expose Skills as MCP tools (v1: always False).
    """

    enabled: bool = False
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8090
    expose_skills: bool = False


@dataclass
class MCPClientConfig:
    """Configuration for connecting to an external MCP server.

    Attributes:
        name: Unique identifier for this connection (e.g. 'filesystem', 'github').
        transport: Transport mechanism — 'stdio' or 'sse'.
        command: Executable for stdio transport (e.g. 'npx', 'python').
        args: Arguments for the stdio command.
        env: Environment variables for the stdio subprocess.
        url: URL for SSE transport (e.g. 'https://example.com/sse').
        headers: HTTP headers for SSE transport.
    """

    name: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


def parse_mcp_config(config: dict | None) -> tuple[MCPServerConfig, list[MCPClientConfig]]:
    """Parse MCP section from the project config dict.

    Args:
        config: Full project config dict (from config.yaml). May be None or empty.

    Returns:
        Tuple of (server_config, list_of_client_configs).
        If 'mcp' key is missing, returns defaults (server disabled, empty clients).
    """
    if not config:
        return MCPServerConfig(), []

    mcp_cfg = config.get("mcp", {})
    if not mcp_cfg:
        return MCPServerConfig(), []

    # Parse server config
    server_raw = mcp_cfg.get("server", {})
    server_config = MCPServerConfig(
        enabled=server_raw.get("enabled", False),
        transport=server_raw.get("transport", "stdio"),
        host=server_raw.get("host", "127.0.0.1"),
        port=server_raw.get("port", 8090),
        expose_skills=server_raw.get("expose_skills", False),
    )

    # Parse client configs
    clients_raw = mcp_cfg.get("clients", [])
    client_configs: list[MCPClientConfig] = []
    if clients_raw:
        for entry in clients_raw:
            if not entry:
                continue
            client_configs.append(
                MCPClientConfig(
                    name=entry.get("name", "unnamed"),
                    transport=entry.get("transport", "stdio"),
                    command=entry.get("command"),
                    args=entry.get("args", []),
                    env=entry.get("env", {}),
                    url=entry.get("url"),
                    headers=entry.get("headers", {}),
                )
            )

    return server_config, client_configs
