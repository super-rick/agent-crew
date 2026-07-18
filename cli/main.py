"""
AgentCrew MCN CLI — main entry point.

Usage:
    agentcrew-mcn write generate --topic "xxx" --style technical
    agentcrew-mcn publish post --content "xxx" --platform juejin
    agentcrew-mcn schedule start --topic-file topics.txt --platform juejin --interval 6
    agentcrew-mcn rag ingest --file article.md --source "my_blog"
    agentcrew-mcn init
"""

import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()

# --- .env loading (from CWD, where `agentcrew-mcn init` creates it) ---
_env_path = Path.cwd() / ".env"
if _env_path.exists():
    with open(_env_path, "r") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                _key = _key.strip()
                _val = _val.strip().strip("\"'")
                if _key and not os.environ.get(_key):
                    os.environ[_key] = _val

# Add project root to Python path (for dev mode: python -m cli.main)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli.analyst import analyst_group  # noqa: E402
from cli.init import init_command  # noqa: E402
from cli.publish import publish_group  # noqa: E402
from cli.rag_cmd import rag_group  # noqa: E402
from cli.schedule import schedule_group  # noqa: E402
from cli.write import write_group  # noqa: E402
from crew_mcp.cli import mcp_group  # noqa: E402

# --- Config search paths (in priority order, for default config) ---
CONFIG_SEARCH_PATHS = [
    Path.cwd() / "config.yaml",
    Path.home() / ".config" / "agentcrew-mcn" / "config.yaml",
    Path.home() / ".agentcrew-mcn" / "config.yaml",
]


def load_config(config_path: str) -> "tuple[dict, Path | None]":
    """Load YAML configuration. Returns (config_dict, resolved_path).

    Search order (when config_path == default "config.yaml"):
        1. ./config.yaml
        2. ~/.config/agentcrew-mcn/config.yaml   (XDG)
        3. ~/.agentcrew-mcn/config.yaml          (legacy dotfile)

    When --config is explicitly given, only that path is tried.
    Returns ({}, None) if no config file is found anywhere.
    """
    import yaml

    path = Path(config_path)

    # Explicit path: only try that one
    if config_path != "config.yaml":
        if not path.exists():
            console.print(f"[red]Error:[/red] Config file not found: {config_path}")
            console.print(
                "[yellow]Hint:[/yellow] Run [bold]agentcrew-mcn init[/bold] to create one."
            )
            return {}, None
        content = path.read_text(encoding="utf-8")
        content = _substitute_env_vars(content)
        return (yaml.safe_load(content) or {}), path.resolve()

    # Default path: search multiple locations
    for search_path in CONFIG_SEARCH_PATHS:
        if search_path.exists():
            content = search_path.read_text(encoding="utf-8")
            content = _substitute_env_vars(content)
            return (yaml.safe_load(content) or {}), search_path.resolve()

    # Not found anywhere
    console.print()
    console.print(
        Panel.fit(
            "\n".join(
                [
                    "No configuration file found in any of:",
                    f"  [dim]• {CONFIG_SEARCH_PATHS[0]}[/dim]",
                    f"  [dim]• {CONFIG_SEARCH_PATHS[1]}[/dim]",
                    f"  [dim]• {CONFIG_SEARCH_PATHS[2]}[/dim]",
                    "",
                    "[bold]Run this to get started:[/bold]",
                    "  [cyan]agentcrew-mcn init[/cyan]",
                    "",
                    "Or specify a config file explicitly:",
                    "  [cyan]agentcrew-mcn --config /path/to/config.yaml write generate ...[/cyan]",
                ]
            ),
            title="[yellow]Configuration Required[/yellow]",
            border_style="yellow",
        )
    )
    console.print()
    return {}, None


def _substitute_env_vars(content: str) -> str:
    """Replace ${ENV_VAR} placeholders with environment variable values."""
    import re

    def _replace_env(match):
        env_var = match.group(1)
        return os.environ.get(env_var, "")

    return re.sub(r"\$\{(\w+)\}", _replace_env, content)


def _init_mcp_clients(config: dict, writer) -> None:
    """Discover MCP tools from configured external servers and inject them.

    Connects to all configured MCP servers (stdio/SSE), discovers their
    tools, converts them to AgentCrew Tool format, and registers them
    in the writer's ToolRegistry. Built-in tools take precedence over
    MCP-discovered tools with the same name.

    Failures are non-fatal — a warning is logged and the system continues
    without MCP tools.
    """
    from crew_mcp.config import parse_mcp_config

    _, client_configs = parse_mcp_config(config)

    if not client_configs:
        return

    try:
        from crew_mcp.client import MCPClientManager

        manager = MCPClientManager(client_configs)
        mcp_tools = manager.connect_all_sync()

        # Inject MCP tools into writer's ToolRegistry
        # Skip tools whose names collide with built-in tools
        builtin_names = set(writer.tool_registry.list_names())
        skipped = 0
        for tool in mcp_tools:
            if tool.name in builtin_names:
                skipped += 1
                continue
            writer.tool_registry.register(tool)

        connected = len(manager.connections)
        registered = len(mcp_tools) - skipped
        if connected > 0:
            console.print(
                f"[green]✓[/green] MCP: [bold]{connected}[/bold] server(s) connected, "
                f"[bold]{registered}[/bold] tool(s) registered"
                + (f" ([dim]{skipped} skipped due to name conflict[/dim])" if skipped else "")
            )
    except ImportError:
        console.print(
            "[yellow]⚠[/yellow] MCP SDK not installed. "
            "Run [bold]pip install mcp[/bold] to enable MCP client support."
        )
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] MCP client init skipped: {e}")


def setup_orchestrator(config: dict) -> tuple:
    """Initialize all components and return (orchestrator, writer, publisher, kb, retriever, analyst)."""  # noqa: E501
    from agents.analyst import AnalystAgent
    from agents.publisher import PublisherAgent
    from agents.writer import WriterAgent
    from llm.client import LLMClient, LLMConfig
    from orchestrator.manager import Orchestrator
    from rag.embedder import create_embedder
    from rag.knowledge_base import KnowledgeBase

    # --- LLM Client ---
    llm_cfg = config.get("llm", {})
    api_key = llm_cfg.get("api_key") or os.environ.get("DEEPSEEK_API_KEY", "")
    llm_client = LLMClient(
        LLMConfig(
            api_key=api_key,
            base_url=llm_cfg.get("base_url", "https://api.deepseek.com/v1"),
            model=llm_cfg.get("model", "deepseek-chat"),
            temperature=llm_cfg.get("temperature", 0.8),
            max_tokens=llm_cfg.get("max_tokens", 4096),
        )
    )

    # --- RAG ---
    from rag.retriever import Retriever

    kb = None
    retriever = None
    rag_cfg = config.get("rag", {})
    if rag_cfg.get("enabled", True):
        embedding_cfg = rag_cfg.get("embedding", {})
        try:
            embedder = create_embedder(embedding_cfg)
        except ValueError as e:
            console.print(f"[yellow]⚠ RAG 未启用: {e}[/yellow]")
            embedder = None

        if embedder:
            kb = KnowledgeBase(
                persist_dir=rag_cfg.get("chroma_persist_dir", "data/chroma"),
                embedder=embedder,
                collection_name=rag_cfg.get("collection_name", "agentcrew_mcn_kb"),
            )
            retriever = Retriever(kb)

    # --- Agents ---
    writer = WriterAgent(
        llm_client=llm_client,
        config=config.get("agents", {}).get("writer", {}),
        kb=kb,
    )

    publisher = PublisherAgent(
        llm_client=llm_client,
        config=config.get("agents", {}).get("publisher", {}),
    )

    # Register platform adapters
    platform_configs = config.get("platforms", {})
    for platform_name, plat_cfg in platform_configs.items():
        if not plat_cfg:
            continue
        try:
            if platform_name == "juejin":
                from platforms.juejin import JuejinAdapter

                publisher.register_platform(platform_name, JuejinAdapter(plat_cfg))
            elif platform_name == "zhihu":
                from platforms.zhihu import ZhihuAdapter

                publisher.register_platform(platform_name, ZhihuAdapter(plat_cfg))
            elif platform_name == "devto":
                from platforms.devto import DevToAdapter

                publisher.register_platform(platform_name, DevToAdapter(plat_cfg))
        except ImportError as e:
            console.print(f"  [yellow][WARN][/yellow] Platform '{platform_name}' not loaded: {e}")

    # --- Analyst Agent ---
    analyst = AnalystAgent(
        llm_client=llm_client,
        config=config.get("agents", {}).get("analyst", {}),
    )

    # --- MCP Client Integration ---
    _init_mcp_clients(config, writer)

    # --- Orchestrator ---
    orchestrator = Orchestrator(config=config.get("orchestrator", {}))
    orchestrator.register_agent(writer)
    orchestrator.register_agent(publisher)
    orchestrator.register_agent(analyst)

    return orchestrator, writer, publisher, kb, retriever, analyst


@click.group()
@click.option("--config", "-c", default="config.yaml", help="Configuration file path")
@click.pass_context
def main(ctx, config):
    """AgentCrew MCN — AI MCN 自动推广工具。

    \b
    你的 AI 营销团队，24 小时在线工作，不领工资。

    \b
    使用方式:
        agentcrew-mcn write generate --topic "主题"
        agentcrew-mcn publish post --content "内容" --platform juejin
        agentcrew-mcn schedule start --topic-file topics.txt
        agentcrew-mcn rag ingest --file document.md

    \b
    首次使用:
        agentcrew-mcn init          # 创建配置文件模板
        # 编辑 .env，填入 API Key
        agentcrew-mcn write generate --topic "Hello World"
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config

    # init command doesn't need config — skip loading to avoid misleading error
    if ctx.invoked_subcommand == "init":
        return

    # Load configuration
    cfg, resolved_path = load_config(config)
    ctx.obj["config"] = cfg

    # Show which config was loaded (when not in CWD)
    if resolved_path and resolved_path != Path.cwd() / "config.yaml":
        console.print(f"[dim]Using config: {resolved_path}[/dim]")

    # Setup orchestrator and components
    if cfg:
        try:
            orch, writer, publisher, kb, retriever, analyst = setup_orchestrator(cfg)
            ctx.obj["orchestrator"] = orch
            ctx.obj["writer"] = writer
            ctx.obj["publisher"] = publisher
            ctx.obj["analyst"] = analyst
            ctx.obj["kb"] = kb
            ctx.obj["retriever"] = retriever
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to initialize: {e}")
            console.print("[yellow]Hint:[/yellow] Check your config.yaml and .env settings.")


# Register command groups
main.add_command(write_group, name="write")
main.add_command(publish_group, name="publish")
main.add_command(schedule_group, name="schedule")
main.add_command(rag_group, name="rag")
main.add_command(analyst_group, name="analyst")
main.add_command(init_command, name="init")
main.add_command(mcp_group, name="mcp")

if __name__ == "__main__":
    main()
