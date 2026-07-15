"""Data loading layer for the Dashboard.

Reads from the project's data files (post_history.json, chroma/, config.yaml)
and returns structured data for the UI. All functions degrade gracefully when
files are missing or malformed.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

import yaml

# Project root is two levels up from dashboard/data_loader.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env at import time (mirrors cli/main.py behaviour) so that
# ${ENV_VAR} placeholders in config.yaml resolve correctly.
_env_path = PROJECT_ROOT / ".env"
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


# ── Config ──────────────────────────────────────────────────


def load_config() -> dict:
    """Load config.yaml with ${ENV_VAR} substitution."""
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    def _replace_env(match):
        return os.environ.get(match.group(1), "")

    content = re.sub(r"\$\{(\w+)\}", _replace_env, content)
    return yaml.safe_load(content) or {}


def has_api_key() -> bool:
    """Check if the DeepSeek API key is available."""
    cfg = load_config()
    api_key = cfg.get("llm", {}).get("api_key", "")
    return bool(api_key) or bool(os.environ.get("DEEPSEEK_API_KEY"))


# ── Post History ────────────────────────────────────────────


def load_post_history() -> list[dict]:
    """Load the post history from data/post_history.json.

    Returns an empty list if the file is missing or malformed.
    """
    path = PROJECT_ROOT / "data" / "post_history.json"
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


# ── RAG Stats ───────────────────────────────────────────────


def get_rag_stats() -> dict | None:
    """Get knowledge base statistics if ChromaDB is available.

    Returns None when ChromaDB or the persist directory is unavailable.
    """
    chroma_dir = PROJECT_ROOT / "data" / "chroma"
    if not chroma_dir.exists():
        return None

    try:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        collections = client.list_collections()
        stats = {
            "persist_dir": str(chroma_dir),
            "collection_count": len(collections),
            "collections": [],
        }
        for col in collections:
            try:
                stats["collections"].append({
                    "name": col.name,
                    "count": col.count(),
                })
            except Exception:
                stats["collections"].append({"name": col.name, "count": "?"})
        return stats
    except Exception:
        return None


# ── Platform Status ─────────────────────────────────────────


def get_platform_configs() -> dict[str, dict]:
    """Return platform configuration from config.yaml (API keys masked)."""
    cfg = load_config()
    platforms = cfg.get("platforms", {})
    result = {}
    for name, plat_cfg in platforms.items():
        masked = {}
        for k, v in (plat_cfg or {}).items():
            if any(secret in k.lower() for secret in ("key", "secret", "cookie", "token")):
                masked[k] = "***" + (v[-4:] if isinstance(v, str) and len(v) > 4 else "")
            else:
                masked[k] = v
        masked["_configured"] = bool(plat_cfg)
        result[name] = masked
    return result


# ── Agent Config ────────────────────────────────────────────


def get_agent_configs() -> dict:
    """Return agent configuration summary."""
    cfg = load_config()
    return cfg.get("agents", {})


# ── Log File ────────────────────────────────────────────────


def get_recent_logs(lines: int = 50) -> str:
    """Return the most recent lines from the log file.

    Returns an empty string if the log file is missing or empty.
    """
    log_path = PROJECT_ROOT / "data" / "logs" / "agentcrew.log"
    if not log_path.exists():
        return ""
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        return "".join(all_lines[-lines:])
    except OSError:
        return ""


# ── Data Freshness ──────────────────────────────────────────


def get_data_freshness() -> str:
    """Return the last-modified time of post_history.json as ISO string,
    or None if the file doesn't exist."""
    path = PROJECT_ROOT / "data" / "post_history.json"
    if not path.exists():
        return None
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
