"""
CLI commands for MCP protocol integration.

Usage:
    agentcrew-mcn mcp serve [--transport stdio|sse]
    agentcrew-mcn mcp list-tools
    agentcrew-mcn mcp status
"""

from __future__ import annotations

import asyncio
import logging

import click
from rich.console import Console
from rich.table import Table

from agents.tools import BUILTIN_TOOLS
from crew_mcp.config import MCPServerConfig

console = Console()
logger = logging.getLogger(__name__)


def _load_config_from_context(ctx: click.Context) -> dict:
    """Load config from Click context, returning empty dict if not available."""
    if ctx.obj and "config" in ctx.obj:
        return ctx.obj.get("config", {})
    return {}


@click.group(name="mcp")
def mcp_group():
    """MCP protocol: serve tools and connect external servers.

    \b
    Commands:
        serve       Start MCP server to expose AgentCrew tools
        list-tools  List all available tools (built-in + MCP-connected)
        status      Show MCP client connection status
    """


@mcp_group.command("serve")
@click.option(
    "--transport",
    default="stdio",
    type=click.Choice(["stdio", "sse"]),
    help="Transport mechanism (default: stdio)",
)
@click.option("--host", default="127.0.0.1", help="Host for SSE transport")
@click.option("--port", default=8090, type=int, help="Port for SSE transport")
@click.pass_context
def serve(ctx, transport, host, port):
    """Start MCP server to expose AgentCrew tools.

    \b
    Stdio mode (default):
        Run as a subprocess for Claude Desktop / Continue.
        agentcrew-mcn mcp serve

    \b
    SSE mode:
        Start an HTTP server for web-based clients.
        agentcrew-mcn mcp serve --transport sse --port 8090
    """
    from agents.tools import ToolRegistry
    from crew_mcp.server import MCPServer

    # Create a minimal ToolRegistry with BUILTIN_TOOLS
    registry = ToolRegistry()
    for tool in BUILTIN_TOOLS:
        registry.register(tool)

    server_config = MCPServerConfig(
        enabled=True,
        transport=transport,
        host=host,
        port=port,
    )

    server = MCPServer(registry, config=server_config)
    tool_count = len(registry)
    console.print(
        f"[bold green]AgentCrew MCP Server[/bold green] — "
        f"exposing [bold]{tool_count}[/bold] tools over [bold]{transport}[/bold]"
    )

    if transport == "stdio":
        console.print("[dim]Connected to MCP client via stdio. Waiting for requests...[/dim]")
        asyncio.run(server.run_stdio())
    elif transport == "sse":
        console.print(f"[dim]Listening on http://{host}:{port}/sse[/dim]")
        asyncio.run(server.run_sse())


@mcp_group.command("list-tools")
@click.pass_context
def list_tools(ctx):
    """List all available tools (built-in + MCP-connected)."""
    config = _load_config_from_context(ctx)

    # Built-in tools
    builtin_table = Table(title="🔧 Built-in Tools")
    builtin_table.add_column("Name", style="cyan")
    builtin_table.add_column("Description", style="dim")
    builtin_table.add_column("Parameters", style="yellow")

    for tool in BUILTIN_TOOLS:
        params = ", ".join(tool.parameters.get("properties", {}).keys())
        builtin_table.add_row(tool.name, tool.description, params or "(none)")

    console.print(builtin_table)

    # MCP-connected tools (if any configured)
    mcp_cfg = config.get("mcp", {})
    clients = mcp_cfg.get("clients", [])
    if clients:
        console.print()
        console.print("[bold]MCP Client Connections (configured):[/bold]")
        for client_cfg in clients:
            transport = client_cfg.get("transport", "stdio")
            detail = (
                f"command: {client_cfg.get('command', '?')}"
                if transport == "stdio"
                else f"url: {client_cfg.get('url', '?')}"
            )
            console.print(
                f"  [cyan]{client_cfg.get('name', '?')}[/cyan] " f"({transport}) — {detail}"
            )
        console.print()
        console.print(
            "[dim]Run [bold]agentcrew-mcn mcp status[/bold] "
            "to check connection state at runtime.[/dim]"
        )
    else:
        console.print()
        console.print(
            "[dim]No MCP clients configured. Add them in config.yaml under mcp.clients.[/dim]"
        )


@mcp_group.command("status")
@click.pass_context
def status(ctx):
    """Show MCP client connection status."""
    config = _load_config_from_context(ctx)

    mcp_cfg = config.get("mcp", {})
    server_cfg = mcp_cfg.get("server", {})

    # Server status
    console.print("[bold]MCP Server[/bold]")
    if server_cfg.get("enabled", False):
        transport = server_cfg.get("transport", "stdio")
        host = server_cfg.get("host", "127.0.0.1")
        port = server_cfg.get("port", 8090)
        console.print("  Status: [green]Enabled[/green]")
        console.print(f"  Transport: {transport}")
        if transport == "sse":
            console.print(f"  Endpoint: http://{host}:{port}/sse")
    else:
        console.print("  Status: [dim]Disabled[/dim]")

    # Client status
    console.print()
    console.print("[bold]MCP Clients[/bold]")

    clients = mcp_cfg.get("clients", [])
    if not clients:
        console.print("  [dim]No MCP clients configured.[/dim]")
        return

    table = Table(title="Configured MCP Client Connections")
    table.add_column("Name", style="cyan")
    table.add_column("Transport", style="green")
    table.add_column("Detail")
    table.add_column("Status", style="yellow")

    for client_cfg in clients:
        name = client_cfg.get("name", "?")
        transport = client_cfg.get("transport", "stdio")

        if transport == "stdio":
            detail = f"{client_cfg.get('command', '?')} {' '.join(client_cfg.get('args', []))}"
        else:
            detail = client_cfg.get("url", "?")

        # Connection status can only be checked at runtime
        table.add_row(name, transport, detail, "[dim]not connected[/dim]")

    console.print(table)
    console.print()
    console.print(
        "[dim]Connection status is checked at runtime. "
        "Use [bold]agentcrew-mcn write generate ...[/bold] to trigger MCP tool discovery.[/dim]"
    )
