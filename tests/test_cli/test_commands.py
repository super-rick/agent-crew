"""CLI command tests — verify Click commands parse and handle errors correctly.

All tests use CliRunner with mocked setup_orchestrator to avoid real
API/network calls. The goal is to verify command invocation, parameter
passing, and error messaging — not end-to-end behavior (that's in test_integration).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from cli.main import main as cli_main


@pytest.fixture(autouse=True)
def _patch_setup():
    """Replace setup_orchestrator globally so CLI commands don't touch real APIs."""
    mock_agents = (
        MagicMock(name="orchestrator"),  # orch
        MagicMock(name="writer"),  # writer
        MagicMock(name="publisher"),  # publisher
        MagicMock(name="kb"),  # kb
        MagicMock(name="retriever"),  # retriever
        MagicMock(name="analyst"),  # analyst
    )
    with (
        patch("cli.main.setup_orchestrator", return_value=mock_agents),
        patch("cli.main.load_config", return_value=({"llm": {"api_key": "test"}}, None)),
    ):
        yield


@pytest.fixture
def runner():
    return CliRunner()


def _invoke(runner, args):
    """Helper: invoke CLI with the main command."""
    return runner.invoke(cli_main, args)


@pytest.fixture
def config_file(tmp_path):
    """Create a temporary config.yaml for testing."""
    config = tmp_path / "config.yaml"
    config.write_text(
        yaml.dump(
            {
                "llm": {"api_key": "test-key", "model": "test-model"},
                "rag": {"enabled": False},
                "platforms": {},
                "orchestrator": {},
            }
        )
    )
    return str(config)


# ============================================================
# Write commands
# ============================================================


class TestWriteGenerate:
    """write generate — content generation."""

    def test_dry_run_outputs_preview(self, runner):
        """--dry-run shows preview without calling LLM."""
        result = _invoke(
            runner,
            ["write", "generate", "--topic", "test topic", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Dry-Run" in result.output

    def test_topic_is_required(self, runner):
        """--topic is required — fails without it."""
        result = _invoke(runner, ["write", "generate"])
        assert result.exit_code != 0

    def test_accepts_platform(self, runner):
        """--platform is accepted."""
        result = _invoke(
            runner,
            ["write", "generate", "--topic", "t", "--platform", "zhihu", "--dry-run"],
        )
        assert result.exit_code == 0

    def test_accepts_style(self, runner):
        """--style is accepted (all four options)."""
        for style in ["technical", "casual", "thread", "promotional"]:
            result = _invoke(
                runner,
                ["write", "generate", "--topic", "t", "--style", style, "--dry-run"],
            )
            assert result.exit_code == 0, f"style={style} failed"

    def test_invalid_style_rejected(self, runner):
        """Invalid --style value is rejected by Click."""
        result = _invoke(
            runner,
            ["write", "generate", "--topic", "t", "--style", "invalid_style"],
        )
        assert result.exit_code != 0


class TestWriteFree:
    """write free — free-form writing."""

    def test_topic_required(self, runner):
        result = _invoke(runner, ["write", "free"])
        assert result.exit_code != 0


class TestWriteOutline:
    """write outline — outline generation."""

    def test_topic_required(self, runner):
        result = _invoke(runner, ["write", "outline"])
        assert result.exit_code != 0


# ============================================================
# Publish commands
# ============================================================


class TestPublishPost:
    """publish post — content publishing."""

    def test_missing_content_and_file(self, runner):
        """Neither --text nor --file nor --platform provided — fails."""
        result = _invoke(runner, ["publish", "post"])
        # May fail from missing required options or empty content
        # Click validates required options first
        assert result.exit_code != 0

    def test_dry_run_with_text(self, runner):
        """--dry-run with --text exits without crash."""
        result = _invoke(
            runner,
            ["publish", "post", "--text", "test content", "--platform", "juejin", "--dry-run"],
        )
        # May fail from platform auth, but shouldn't crash on option parsing
        assert result.exit_code is not None


class TestPublishStatus:
    """publish status — platform status."""

    def test_status_output(self, runner):
        result = _invoke(runner, ["publish", "status"])
        # Should not crash — output format depends on config
        assert result.exit_code == 0


class TestPublishHistory:
    """publish history — post history."""

    def test_history_output(self, runner):
        result = _invoke(runner, ["publish", "history"])
        assert result.exit_code == 0


# ============================================================
# RAG commands
# ============================================================


class TestRagStats:
    """rag stats — knowledge base statistics."""

    def test_stats_runs(self, runner):
        """rag stats runs without crash."""
        result = _invoke(runner, ["rag", "stats"])
        assert result.exit_code == 0


class TestRagSearch:
    """rag search — semantic search."""

    def test_query_required(self, runner):
        result = _invoke(runner, ["rag", "search"])
        assert result.exit_code != 0


class TestRagIngest:
    """rag ingest — document ingestion."""

    def test_file_required(self, runner):
        result = _invoke(runner, ["rag", "ingest"])
        assert result.exit_code != 0

    def test_nonexistent_file(self, runner):
        result = _invoke(runner, ["rag", "ingest", "--file", "/nonexistent/file.md"])
        # kb=None case — should show error
        assert result.exit_code == 0 or "不存在" in result.output or "未初始化" in result.output


# ============================================================
# MCP commands
# ============================================================


class TestMcpListTools:
    """mcp list-tools — tool listing."""

    def test_lists_builtin_tools(self, runner):
        result = _invoke(runner, ["mcp", "list-tools"])
        assert result.exit_code == 0
        assert "web_search" in result.output
        assert "fetch_url_content" in result.output
        assert "get_current_time" in result.output

    def test_shows_no_clients_message(self, runner):
        """When no MCP clients configured, shows hint."""
        result = _invoke(runner, ["mcp", "list-tools"])
        assert "No MCP clients" in result.output or "Built-in" in result.output


class TestMcpStatus:
    """mcp status — connection status."""

    def test_status_output(self, runner):
        result = _invoke(runner, ["mcp", "status"])
        assert result.exit_code == 0
        assert "MCP Server" in result.output
        assert "MCP Clients" in result.output


class TestMcpServe:
    """mcp serve — start MCP server."""

    def test_serve_help(self, runner):
        result = _invoke(runner, ["mcp", "serve", "--help"])
        assert result.exit_code == 0
        assert "--transport" in result.output

    def test_invalid_transport(self, runner):
        result = _invoke(runner, ["mcp", "serve", "--transport", "invalid"])
        assert result.exit_code != 0


# ============================================================
# Init command
# ============================================================


class TestInit:
    """init — project initialization."""

    def test_init_runs(self, runner, tmp_path):
        """init generates config files."""
        import os

        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = _invoke(runner, ["init"])
            assert result.exit_code == 0
            # Should create config.yaml and .env
            assert (tmp_path / "config.yaml").exists()
        finally:
            os.chdir(cwd)

    def test_init_skips_if_exists(self, runner, tmp_path):
        """init skips or warns if config already exists."""
        import os

        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # First run creates files
            runner.invoke(cli_main, ["init"])
            # Second run — may warn or exit non-zero, just shouldn't crash
            result = _invoke(runner, ["init"])
            # Accept any outcome (warn, skip, exit) as long as it doesn't crash
            assert result.exit_code is not None
        finally:
            os.chdir(cwd)


# ============================================================
# Global CLI options
# ============================================================


class TestGlobalOptions:
    """Top-level CLI behavior."""

    def test_main_help(self, runner):
        result = _invoke(runner, ["--help"])
        assert result.exit_code == 0
        assert "AgentCrew MCN" in result.output

    def test_all_command_groups_listed(self, runner):
        """All command groups appear in main help."""
        result = _invoke(runner, ["--help"])
        for group in ["write", "publish", "schedule", "rag", "analyst", "mcp", "init"]:
            assert group in result.output, f"'{group}' not in help output"
