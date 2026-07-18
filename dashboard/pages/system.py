"""System status page — platform connections, RAG stats, config, logs."""

from __future__ import annotations

import streamlit as st

from dashboard.data_loader import (
    get_agent_configs,
    get_platform_configs,
    get_rag_stats,
    get_recent_logs,
    has_api_key,
    load_config,
)


def main() -> None:
    st.title("⚙️ 系统状态")
    st.caption("平台连接、RAG 知识库、配置和日志")

    # ── Overall Status ──
    st.subheader("🔌 服务状态")

    api_ok = has_api_key()
    cfg = load_config()
    rag_stats = get_rag_stats()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LLM API", "✅ 已配置" if api_ok else "❌ 未配置")
    c2.metric("RAG 知识库", f"{rag_stats['collection_count']} 集合" if rag_stats else "❌ 未启用")
    c3.metric(
        "配置版本",
        f"{cfg.get('orchestrator', {}).get('schedule_interval_min', '?')}min 间隔" if cfg else "?",
    )
    c4.metric("Python", "3.9+")

    # ── Platform Status ──
    st.subheader("📡 平台适配器")
    platforms = get_platform_configs()
    if platforms:
        for name, pcfg in platforms.items():
            configured = pcfg.pop("_configured", False)
            icon = "✅" if configured else "⏳"
            with st.expander(f"{icon} **{name}**"):
                if configured:
                    st.json(pcfg)
                else:
                    st.caption("未配置凭证 — 请检查 config.yaml")
    else:
        st.info("未检测到任何平台配置。")

    # ── Agent Status ──
    st.subheader("🤖 AI 员工")
    agents = get_agent_configs()
    if agents:
        cols = st.columns(len(agents))
        for i, (name, acfg) in enumerate(agents.items()):
            enabled = acfg.get("enabled", True) if isinstance(acfg, dict) else True
            with cols[i]:
                st.metric(
                    label=name.capitalize(),
                    value="✅ 在线" if enabled else "⏳ 离线",
                )
    else:
        st.info("暂无 Agent 配置。")

    # ── RAG Stats ──
    st.subheader("🧠 RAG 知识库")
    if rag_stats:
        st.markdown(f"**存储路径**: `{rag_stats['persist_dir']}`")
        st.markdown(f"**集合数**: {rag_stats['collection_count']}")
        for col_info in rag_stats.get("collections", []):
            st.markdown(f"- **{col_info['name']}**: {col_info['count']} 条文档")
    else:
        st.info("RAG 知识库未启用或无数据。使用 `agentcrew-mcnrag ingest --file doc.md` 添加文档。")

    # ── Config Overview ──
    st.subheader("📋 配置概览")
    if cfg:
        # Show a safe subset of config
        safe_cfg = {
            "llm": {k: v for k, v in cfg.get("llm", {}).items() if k != "api_key"},
            "orchestrator": cfg.get("orchestrator", {}),
            "rag": cfg.get("rag", {}),
        }
        st.json(safe_cfg)
    else:
        st.info("config.yaml 未找到。")

    # ── Logs ──
    st.subheader("📜 最近日志")
    logs = get_recent_logs(50)
    if logs:
        st.code(logs, language="log", line_numbers=True)
    else:
        st.info("暂无日志记录。")


if __name__ == "__main__":
    main()
