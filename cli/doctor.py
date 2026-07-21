"""
CLI — doctor command. Diagnoses AgentCrew configuration health.

Usage:
    agentcrew-mcn doctor              # Check all
    agentcrew-mcn doctor --quick      # Skip network checks (API calls)
    agentcrew-mcn doctor --json       # Machine-readable output

Each check returns (status, message, fix_hint) where status is one of:
    ok / warning / error / info
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cli.i18n import _

console = Console()

# Status icons (same in zh/en — visual only)
ICONS = {"ok": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}


@dataclass
class CheckResult:
    """Result of a single health check."""

    name: str
    status: str  # ok | warning | error | info
    message: str
    fix_hint: str = ""

    @property
    def icon(self) -> str:
        return ICONS.get(self.status, "❓")


def _find_config() -> Path | None:
    """Find config.yaml using same search logic as main.py."""
    search = [
        Path.cwd() / "config.yaml",
        Path.home() / ".config" / "agentcrew-mcn" / "config.yaml",
        Path.home() / ".agentcrew-mcn" / "config.yaml",
    ]
    for p in search:
        if p.exists():
            return p
    return None


def _load_config() -> tuple[dict, Path | None]:
    """Load config, returning (dict, source_path)."""
    import re

    import yaml

    path = _find_config()
    if not path:
        return {}, None

    content = path.read_text(encoding="utf-8")

    def _sub(m):
        return os.environ.get(m.group(1), "")

    content = re.sub(r"\$\{(\w+)\}", _sub, content)
    return (yaml.safe_load(content) or {}), path


# ── Individual Checks ────────────────────────────────────────


def _check_config_file(config: dict, config_path: Path | None) -> CheckResult:
    if config_path and config_path.exists():
        return CheckResult(
            name=_("doctor.config_file"),
            status="ok",
            message=str(config_path),
        )
    return CheckResult(
        name=_("doctor.config_file"),
        status="error",
        message=_("doctor.not_found"),
        fix_hint=_("doctor.fix_init"),
    )


def _check_env_file(config: dict, config_path: Path | None) -> CheckResult:
    env_path = (config_path.parent if config_path else Path.cwd()) / ".env"
    if env_path.exists():
        return CheckResult(
            name=_("doctor.env_file"),
            status="ok",
            message=str(env_path),
        )
    return CheckResult(
        name=_("doctor.env_file"),
        status="warning",
        message=_("doctor.env_not_found"),
        fix_hint=_("doctor.fix_init"),
    )


def _check_llm(config: dict) -> CheckResult:
    """Check LLM API key and optionally validate it."""
    llm_cfg = config.get("llm", {})
    provider = llm_cfg.get("provider", "deepseek")
    api_key = llm_cfg.get("api_key") or os.environ.get("DEEPSEEK_API_KEY", "")

    name = _("doctor.llm", provider=provider)

    if not api_key:
        return CheckResult(
            name=name,
            status="error",
            message=_("doctor.llm_no_key", key_name="DEEPSEEK_API_KEY"),
        )

    # Quick validation: try a models list call (lightweight)
    try:
        import httpx

        base_url = llm_cfg.get("base_url", "https://api.deepseek.com/v1")
        resp = httpx.get(
            f"{base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5,
        )
        if resp.status_code == 200:
            balance = ""
            # Try to get balance info if available (DeepSeek-specific)
            try:
                bal_resp = httpx.get(
                    "https://api.deepseek.com/user/balance",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=5,
                )
                if bal_resp.status_code == 200:
                    bdata = bal_resp.json()
                    if bdata.get("is_available"):
                        for info in bdata.get("balance_infos", []):
                            bal = info.get("total_balance", "?")
                            balance = _("doctor.llm_balance", balance=bal)
                            break
            except Exception:
                pass

            return CheckResult(
                name=name,
                status="ok",
                message=_("doctor.llm_ok", balance=balance),
            )
        else:
            return CheckResult(
                name=name,
                status="error",
                message=_(
                    "doctor.llm_auth_failed",
                    error=f"HTTP {resp.status_code}",
                    url="https://platform.deepseek.com",
                ),
            )
    except Exception as e:
        # Network error — key might still be valid, just can't verify
        return CheckResult(
            name=name,
            status="warning",
            message=f"API key found but cannot verify (network error: {e})",
        )


def _check_platform(name: str, adapter_class, config: dict) -> CheckResult:
    """Check a single platform adapter's auth status."""
    plat_cfg = config.get("platforms", {}).get(name, {})
    if not plat_cfg:
        return CheckResult(
            name=name,
            status="info",
            message=_("doctor.platform_no_key", platform=name),
        )

    try:
        adapter = adapter_class(plat_cfg)
        ok = adapter.authenticate()
        if ok:
            user = ""
            if hasattr(adapter, "_client") and adapter._client:
                try:
                    # Try to get user info for the message
                    pass
                except Exception:
                    pass
            return CheckResult(
                name=name,
                status="ok",
                message=_("doctor.platform_ok", user=user),
            )
        else:
            status = adapter.get_status()
            msg = status.error_message or "Authentication failed"
            return CheckResult(
                name=name,
                status="error",
                message=_(
                    "doctor.platform_auth_failed",
                    error=msg,
                    fix=f"Run: agentcrew-mcn auth {name}",
                ),
            )
    except Exception as e:
        return CheckResult(
            name=name,
            status="error",
            message=_(
                "doctor.platform_auth_failed",
                error=str(e),
                fix=f"Run: agentcrew-mcn auth {name}",
            ),
        )


def _check_rag(config: dict) -> CheckResult:
    """Check RAG / embedding service."""
    rag_cfg = config.get("rag", {})
    if not rag_cfg.get("enabled", True):
        return CheckResult(
            name=_("doctor.rag", provider="disabled"),
            status="info",
            message="RAG is disabled in config",
        )

    embedding_cfg = rag_cfg.get("embedding", {})
    provider = embedding_cfg.get("provider", "siliconflow") if embedding_cfg else "siliconflow"

    name = _("doctor.rag", provider=provider)

    # Try to create embedder and test
    try:
        from rag.embedder import create_embedder

        embedder = create_embedder(embedding_cfg or {})
        # Quick test: embed a tiny string
        import asyncio

        try:
            asyncio.get_running_loop()
            return CheckResult(name=name, status="ok", message=_("doctor.rag_ok"))
        except RuntimeError:
            # Test sync if possible
            try:
                embedder.embed("test")
                return CheckResult(name=name, status="ok", message=_("doctor.rag_ok"))
            except Exception as e:
                return CheckResult(
                    name=name,
                    status="warning",
                    message=_(
                        "doctor.rag_failed",
                        error=str(e)[:80],
                        fix=_("doctor.fix_embedding_error"),
                    ),
                )
    except ValueError as e:
        return CheckResult(
            name=name,
            status="warning",
            message=_(
                "doctor.rag_failed",
                error=str(e)[:80],
                fix=_("doctor.fix_embedding_config"),
            ),
        )
    except ImportError:
        return CheckResult(
            name=name,
            status="info",
            message="Embedding library not available",
        )


def _check_chromadb(config: dict) -> CheckResult:
    """Check ChromaDB status."""
    rag_cfg = config.get("rag", {})
    persist_dir = rag_cfg.get("chroma_persist_dir", "data/chroma")

    name = _("doctor.chromadb")
    chroma_path = Path(persist_dir)

    if not chroma_path.exists():
        return CheckResult(
            name=name,
            status="info",
            message=_("doctor.chromadb_empty"),
        )

    # Count documents
    try:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.PersistentClient(
            path=str(chroma_path.resolve()),
            settings=Settings(anonymized_telemetry=False),
        )
        collection_name = rag_cfg.get("collection_name", "agentcrew_mcn_kb")
        try:
            collection = client.get_collection(collection_name)
            count = collection.count()
            size_str = _format_size(_dir_size(chroma_path))
            return CheckResult(
                name=name,
                status="ok",
                message=_("doctor.chromadb_ok", count=count, size=size_str),
            )
        except Exception:
            return CheckResult(name=name, status="info", message=_("doctor.chromadb_empty"))
    except ImportError:
        return CheckResult(
            name=name,
            status="warning",
            message="ChromaDB not installed",
        )


def _check_playwright(config: dict) -> CheckResult:
    """Check if Playwright + Chromium is installed."""
    name = _("doctor.playwright")
    try:
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
            return CheckResult(name=name, status="ok", message=_("doctor.playwright_ok"))
        except Exception:
            return CheckResult(name=name, status="warning", message=_("doctor.playwright_missing"))
    except ImportError:
        return CheckResult(name=name, status="warning", message="playwright package not installed")


def _check_mcp(config: dict) -> CheckResult:
    """Check MCP server status."""
    from crew_mcp.config import parse_mcp_config

    server_cfg, client_cfgs = parse_mcp_config(config)
    name = _("doctor.mcp_server")

    if not server_cfg.enabled:
        return CheckResult(name=name, status="info", message=_("doctor.mcp_disabled"))
    return CheckResult(
        name=name,
        status="ok",
        message=_("doctor.mcp_ok", transport=server_cfg.transport),
    )


# ── Helpers ──────────────────────────────────────────────────


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"


def _dir_size(path: Path) -> int:
    """Total size of all files in a directory (recursive)."""
    total = 0
    if path.is_dir():
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    return total


# ── Collector & Runner ───────────────────────────────────────


def _collect_checks(
    config: dict, config_path: Path | None, quick: bool = False
) -> list[CheckResult]:
    """Collect and run all health checks."""
    results: list[CheckResult] = []

    # Always-local checks
    results.append(_check_config_file(config, config_path))
    results.append(_check_env_file(config, config_path))

    if quick:
        results.append(CheckResult(name="ℹ️", status="info", message=_("doctor.quick_mode")))
        return results

    # Network checks (may fail if offline)
    results.append(_check_llm(config))

    # Platform checks — each registered platform gets a health check
    plat_cfg = config.get("platforms", {})
    _platform_adapters = {
        "juejin": ("platforms.juejin", "JuejinAdapter"),
        "zhihu": ("platforms.zhihu", "ZhihuAdapter"),
        "devto": ("platforms.devto", "DevToAdapter"),
        "csdn": ("platforms.csdn", "CsdnAdapter"),
        "segmentfault": ("platforms.segmentfault", "SegmentFaultAdapter"),
        "xiaohongshu": ("platforms.xiaohongshu", "XiaohongshuAdapter"),
        "medium": ("platforms.medium", "MediumAdapter"),
        "x_twitter": ("platforms.x_twitter", "XTwitterAdapter"),
        "wechat": ("platforms.wechat", "WechatAdapter"),
    }
    import importlib

    for pname, (mod_path, cls_name) in _platform_adapters.items():
        if pname not in plat_cfg:
            continue
        try:
            mod = importlib.import_module(mod_path)
            adapter_cls = getattr(mod, cls_name)
            results.append(_check_platform(pname, adapter_cls, config))
        except (ImportError, AttributeError):
            pass

    results.append(_check_rag(config))
    results.append(_check_chromadb(config))
    results.append(_check_playwright(config))
    results.append(_check_mcp(config))

    return results


def run_doctor(config: dict, config_path: Path | None, quick: bool = False) -> list[CheckResult]:
    """Run all health checks and return results."""
    return _collect_checks(config, config_path, quick=quick)


# ── CLI Command ──────────────────────────────────────────────


def _render_rich(results: list[CheckResult]) -> None:
    """Render check results as a rich table."""
    console.print()
    console.print(Panel.fit(_("doctor.title"), border_style="blue"))
    console.print()

    table = Table(show_header=False, padding=(0, 2))
    table.add_column("status", width=3)
    table.add_column("name", width=20)
    table.add_column("detail")

    problems = 0
    fatal = 0

    for r in results:
        if r.status in ("error", "warning"):
            problems += 1
        if r.status == "error":
            fatal += 1

        detail = r.message
        if r.fix_hint:
            detail += f"\n  [dim]→ {r.fix_hint}[/dim]"

        table.add_row(r.icon, f"[bold]{r.name}[/bold]", detail)

    console.print(table)
    console.print()

    if problems == 0:
        console.print(f"[green]{_('doctor.summary_ok')}[/green]")
    else:
        console.print(f"[yellow]{_('doctor.summary', problems=problems, fatal=fatal)}[/yellow]")
    console.print()


def _render_json(results: list[CheckResult]) -> None:
    """Render check results as JSON."""
    output = []
    for r in results:
        output.append(
            {
                "name": r.name,
                "status": r.status,
                "message": r.message,
                "fix_hint": r.fix_hint,
            }
        )
    print(json.dumps(output, ensure_ascii=False, indent=2))


@click.command()
@click.option("--quick", "-q", is_flag=True, help="Skip network checks (API calls)")
@click.option("--json", "json_output", is_flag=True, help="Machine-readable JSON output")
@click.pass_context
def doctor_command(ctx, quick: bool, json_output: bool):
    """Diagnose AgentCrew configuration and connectivity.

    Checks config files, API keys, platform authentication,
    RAG embedding service, ChromaDB, Playwright, and MCP.

    \b
    Examples:
        agentcrew-mcn doctor              # Full health check
        agentcrew-mcn doctor --quick      # Skip network calls
        agentcrew-mcn doctor --json       # JSON output for scripting
    """
    cfg = ctx.obj.get("config", {})
    config_path = _find_config()

    results = run_doctor(cfg, config_path, quick=quick)

    if json_output:
        _render_json(results)
    else:
        _render_rich(results)
