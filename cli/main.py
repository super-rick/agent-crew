"""
AgentCrew CLI — main entry point.

Usage:
    agent-crew write generate --topic "xxx" --style technical
    agent-crew publish post --content "xxx" --platform juejin
    agent-crew schedule start --topic-file topics.txt --platform juejin --interval 6
    agent-crew rag ingest --file article.md --source "my_blog"
"""

import os
import sys
import re
from pathlib import Path

import click

# Load .env file if it exists (before config.yaml resolution)
_env_path = Path(__file__).resolve().parent.parent / ".env"
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

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli.write import write_group
from cli.publish import publish_group
from cli.schedule import schedule_group
from cli.rag_cmd import rag_group


def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    import yaml

    # Try loading the config file
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"Config file not found: {config_path}", file=sys.stderr)
        print("Using default configuration.", file=sys.stderr)
        return {}

    with open(config_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace ${ENV_VAR} with environment variables
    import re

    def _replace_env(match):
        env_var = match.group(1)
        return os.environ.get(env_var, "")

    content = re.sub(r"\$\{(\w+)\}", _replace_env, content)
    return yaml.safe_load(content) or {}


def setup_orchestrator(config: dict) -> tuple:
    """Initialize all components and return (orchestrator, writer, publisher)."""
    from llm.client import LLMClient, LLMConfig
    from agents.writer import WriterAgent
    from agents.publisher import PublisherAgent
    from rag.embedder import DeepSeekEmbedder
    from rag.knowledge_base import KnowledgeBase
    from orchestrator.manager import Orchestrator

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
    if rag_cfg.get("enabled", True) and api_key:
        embedder = DeepSeekEmbedder(
            api_key=api_key,
            base_url=llm_cfg.get("base_url", "https://api.deepseek.com/v1"),
        )
        kb = KnowledgeBase(
            persist_dir=rag_cfg.get("chroma_persist_dir", "data/chroma"),
            embedder=embedder,
            collection_name=rag_cfg.get("collection_name", "agentcrew_kb"),
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
            elif platform_name == "twitter":
                from platforms.twitter import TwitterAdapter
                publisher.register_platform(platform_name, TwitterAdapter(plat_cfg))
        except ImportError as e:
            print(f"  [WARN] Platform '{platform_name}' not loaded: {e}", file=sys.stderr)

    # --- Orchestrator ---
    orchestrator = Orchestrator(config=config.get("orchestrator", {}))
    orchestrator.register_agent(writer)
    orchestrator.register_agent(publisher)

    return orchestrator, writer, publisher, kb, retriever


@click.group()
@click.option("--config", "-c", default="config.yaml", help="Configuration file path")
@click.pass_context
def main(ctx, config):
    """AgentCrew — AI MCN 自动推广工具。

    你的 AI 营销团队，24 小时在线工作，不领工资。

    使用方式:
        agent-crew write generate --topic "主题"
        agent-crew publish post --content "内容" --platform juejin
        agent-crew schedule start --topic-file topics.txt
        agent-crew rag ingest --file document.md
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config

    # Load configuration (lazy — only loaded when a command needs it)
    cfg = load_config(config)
    ctx.obj["config"] = cfg

    # Setup orchestrator and components (lazy)
    if cfg:
        orch, writer, publisher, kb, retriever = setup_orchestrator(cfg)
        ctx.obj["orchestrator"] = orch
        ctx.obj["writer"] = writer
        ctx.obj["publisher"] = publisher
        ctx.obj["kb"] = kb
        ctx.obj["retriever"] = retriever


# Register command groups
main.add_command(write_group, name="write")
main.add_command(publish_group, name="publish")
main.add_command(schedule_group, name="schedule")
main.add_command(rag_group, name="rag")

if __name__ == "__main__":
    main()
