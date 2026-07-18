"""Tests for mcp/config.py — configuration parsing."""

from __future__ import annotations

from crew_mcp.config import (
    MCPClientConfig,
    MCPServerConfig,
    parse_mcp_config,
)


class TestMCPServerConfig:
    """Server config defaults are safe for production."""

    def test_defaults_disabled(self):
        """Server is disabled by default."""
        cfg = MCPServerConfig()
        assert cfg.enabled is False
        assert cfg.transport == "stdio"
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 8090

    def test_sse_config(self):
        """SSE transport config accepts custom host/port."""
        cfg = MCPServerConfig(
            enabled=True,
            transport="sse",
            host="0.0.0.0",
            port=9000,
        )
        assert cfg.enabled is True
        assert cfg.transport == "sse"
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 9000


class TestMCPClientConfig:
    """Client config validation."""

    def test_stdio_client(self):
        """Stdio transport client config."""
        cfg = MCPClientConfig(
            name="filesystem",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            env={"HOME": "/home/user"},
        )
        assert cfg.name == "filesystem"
        assert cfg.transport == "stdio"
        assert cfg.command == "npx"
        assert len(cfg.args) == 3
        assert cfg.env == {"HOME": "/home/user"}

    def test_sse_client(self):
        """SSE transport client config."""
        cfg = MCPClientConfig(
            name="weather",
            transport="sse",
            url="https://weather.example.com/sse",
            headers={"Authorization": "Bearer token123"},
        )
        assert cfg.name == "weather"
        assert cfg.transport == "sse"
        assert cfg.url == "https://weather.example.com/sse"
        assert cfg.headers == {"Authorization": "Bearer token123"}

    def test_defaults(self):
        """Client config uses safe defaults."""
        cfg = MCPClientConfig(name="test")
        assert cfg.transport == "stdio"
        assert cfg.command is None
        assert cfg.args == []
        assert cfg.env == {}
        assert cfg.url is None
        assert cfg.headers == {}


class TestParseMCPConfig:
    """YAML-sourced config dict parsing."""

    def test_empty_config(self):
        """No config returns disabled defaults."""
        server, clients = parse_mcp_config({})
        assert server.enabled is False
        assert clients == []

    def test_none_config(self):
        """None config handled gracefully."""
        server, clients = parse_mcp_config(None)
        assert server.enabled is False
        assert clients == []

    def test_no_mcp_section(self):
        """Config without 'mcp' key returns defaults."""
        server, clients = parse_mcp_config({"llm": {}, "platforms": {}})
        assert server.enabled is False
        assert clients == []

    def test_empty_mcp_section(self):
        """Empty 'mcp' section returns defaults."""
        server, clients = parse_mcp_config({"mcp": {}})
        assert server.enabled is False

    def test_server_enabled(self):
        """Server config parsed correctly."""
        server, clients = parse_mcp_config(
            {
                "mcp": {
                    "server": {
                        "enabled": True,
                        "transport": "sse",
                        "host": "127.0.0.1",
                        "port": 8080,
                    },
                },
            }
        )
        assert server.enabled is True
        assert server.transport == "sse"
        assert server.port == 8080
        assert clients == []

    def test_server_partial_config(self):
        """Partial server config fills defaults."""
        server, clients = parse_mcp_config(
            {
                "mcp": {
                    "server": {
                        "enabled": True,
                    },
                },
            }
        )
        assert server.enabled is True
        assert server.transport == "stdio"  # default
        assert server.port == 8090  # default

    def test_single_stdio_client(self):
        """Single stdio client parsed correctly."""
        server, clients = parse_mcp_config(
            {
                "mcp": {
                    "clients": [
                        {
                            "name": "filesystem",
                            "transport": "stdio",
                            "command": "npx",
                            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/docs"],
                        },
                    ],
                },
            }
        )

        assert len(clients) == 1
        assert clients[0].name == "filesystem"
        assert clients[0].transport == "stdio"
        assert clients[0].command == "npx"
        assert len(clients[0].args) == 3

    def test_single_sse_client(self):
        """Single SSE client parsed correctly."""
        server, clients = parse_mcp_config(
            {
                "mcp": {
                    "clients": [
                        {
                            "name": "remote_tools",
                            "transport": "sse",
                            "url": "https://example.com/sse",
                        },
                    ],
                },
            }
        )

        assert len(clients) == 1
        assert clients[0].transport == "sse"
        assert clients[0].url == "https://example.com/sse"

    def test_multiple_clients(self):
        """Multiple client configs parsed correctly."""
        server, clients = parse_mcp_config(
            {
                "mcp": {
                    "clients": [
                        {"name": "server_a", "transport": "stdio", "command": "python"},
                        {
                            "name": "server_b",
                            "transport": "sse",
                            "url": "http://localhost:3000/sse",
                        },
                    ],
                },
            }
        )

        assert len(clients) == 2
        assert clients[0].name == "server_a"
        assert clients[1].name == "server_b"

    def test_client_with_env_vars(self):
        """Client config with environment variables."""
        server, clients = parse_mcp_config(
            {
                "mcp": {
                    "clients": [
                        {
                            "name": "github",
                            "command": "npx",
                            "args": ["-y", "@modelcontextprotocol/server-github"],
                            "env": {
                                "GITHUB_TOKEN": "gh_token_123",
                            },
                        },
                    ],
                },
            }
        )

        assert clients[0].env == {"GITHUB_TOKEN": "gh_token_123"}

    def test_empty_clients_list(self):
        """Empty clients list returns empty configs."""
        server, clients = parse_mcp_config(
            {
                "mcp": {
                    "clients": [],
                },
            }
        )
        assert clients == []

    def test_server_and_clients_together(self):
        """Both server and clients parsed together."""
        server, clients = parse_mcp_config(
            {
                "mcp": {
                    "server": {"enabled": True, "transport": "sse"},
                    "clients": [
                        {"name": "fs", "command": "npx", "args": ["-y", "server-fs"]},
                    ],
                },
            }
        )

        assert server.enabled is True
        assert server.transport == "sse"
        assert len(clients) == 1
        assert clients[0].name == "fs"
