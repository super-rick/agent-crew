"""Test fixtures for MCP module tests."""

from __future__ import annotations

import pytest

from agents.tools import BUILTIN_TOOLS, Tool, ToolRegistry


@pytest.fixture
def sample_agentcrew_tool() -> Tool:
    """A representative AgentCrew Tool for conversion testing."""
    return Tool(
        name="test_search",
        description="A test search tool for unit testing",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
        func=lambda query, limit=10: f"Searched: {query} (limit={limit})",
    )


@pytest.fixture
def sample_mcp_tool_def() -> dict:
    """A representative MCP tool definition for conversion testing."""
    return {
        "name": "remote_search",
        "description": "A remote search tool from an MCP server",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max results to return",
                },
            },
            "required": ["query"],
        },
    }


@pytest.fixture
def sample_mcp_tool_def_no_type() -> dict:
    """MCP tool def where inputSchema is missing the type field."""
    return {
        "name": "no_type_tool",
        "description": "A tool whose inputSchema lacks a type field",
        "inputSchema": {
            "properties": {
                "text": {"type": "string", "description": "Input text"},
            },
            "required": ["text"],
        },
    }


@pytest.fixture
def sample_mcp_tool_def_empty() -> dict:
    """MCP tool def with empty inputSchema."""
    return {
        "name": "no_param_tool",
        "description": "A tool that takes no parameters",
        "inputSchema": {},
    }


@pytest.fixture
def builtin_tool_registry() -> ToolRegistry:
    """ToolRegistry pre-populated with BUILTIN_TOOLS."""
    registry = ToolRegistry()
    for tool in BUILTIN_TOOLS:
        registry.register(tool)
    return registry
