"""AI Analytics page — data summary, AI-powered reports and recommendations."""

from __future__ import annotations

import streamlit as st

from agents.analyst import AnalystAgent
from dashboard.components import metric_cards
from dashboard.data_loader import has_api_key, load_config, load_post_history


def _build_analyst() -> AnalystAgent | None:
    """Create an AnalystAgent if the API key is available."""
    if not has_api_key():
        return None

    cfg = load_config()
    llm_cfg = cfg.get("llm", {})
    import os

    api_key = llm_cfg.get("api_key") or os.environ.get("DEEPSEEK_API_KEY", "")

    from llm.client import LLMClient, LLMConfig

    llm_client = LLMClient(
        LLMConfig(
            api_key=api_key,
            base_url=llm_cfg.get("base_url", "https://api.deepseek.com/v1"),
            model=llm_cfg.get("model", "deepseek-chat"),
            temperature=llm_cfg.get("temperature", 0.8),
            max_tokens=llm_cfg.get("max_tokens", 4096),
        )
    )

    analyst_config = cfg.get("agents", {}).get("analyst", {})
    return AnalystAgent(llm_client=llm_client, config=analyst_config)


def main() -> None:
    st.title("🤖 AI 分析")
    st.caption("数据驱动的运营分析和策略建议")

    records = load_post_history()

    # ── Data Summary (no LLM needed) ──
    st.subheader("📋 数据摘要")

    col1, col2 = st.columns(2)
    with col1:
        days = st.slider("分析周期（天）", 1, 90, 7, key="analyst_days")
    with col2:
        platforms = sorted({r.get("platform", "?") for r in records})
        selected = st.multiselect("平台", platforms, default=platforms, key="analyst_platforms")

    filtered = [r for r in records if r.get("platform") in selected]

    # Calculate metrics without LLM
    if filtered:
        analyst_stub = AnalystAgent.__new__(AnalystAgent)
        analyst_stub._history_file = ""
        analyst_stub._default_days = days
        metrics = analyst_stub._calculate_metrics(filtered, days)

        metric_cards(
            {
                "total_posts": metrics["total_posts"],
                "success_rate": metrics["success_rate"],
                "platform_count": len(metrics.get("platform_stats", [])),
                "active_days": sum(1 for d in metrics.get("daily_counts", []) if d["total"] > 0),
            }
        )

        # Platform detail table
        if metrics.get("platform_stats"):
            st.markdown("**各平台指标**")
            st.dataframe(
                [{**p, "success_rate": f"{p['success_rate']}%"} for p in metrics["platform_stats"]],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("暂无数据。")

    # ── AI Report Generation (needs LLM) ──
    st.divider()
    st.subheader("🧠 AI 智能分析")

    analyst = _build_analyst()
    if analyst is None:
        st.warning(
            "⚠️ 需要配置 DeepSeek API Key 才能使用 AI 分析功能。\n请在 `.env` 中设置 `DEEPSEEK_API_KEY`。"  # noqa: E501
        )
        return

    # But: passed directly to analyst methods which use self.llm_client
    if not filtered:
        st.info("当前筛选条件下无数据，无法生成分析。")
        return

    tab1, tab2 = st.tabs(["📄 生成周报", "💡 策略建议"])

    with tab1:
        st.markdown("基于当前数据，AI 自动生成内容运营周报。")
        if st.button("🚀 生成周报", type="primary", key="gen_report"):
            with st.spinner("AI 正在分析数据并撰写报告..."):
                try:
                    report = analyst._generate_report({**metrics, "period_days": days})
                    st.success("报告生成完毕")
                    st.markdown(report)
                except Exception as e:
                    st.error(f"报告生成失败: {e}")

    with tab2:
        st.markdown("AI 给出可执行的策略优化建议。")
        if st.button("💡 生成建议", type="primary", key="gen_recommend"):
            with st.spinner("AI 正在分析数据并生成策略建议..."):
                try:
                    recommendations = analyst._generate_recommendations(
                        {**metrics, "period_days": days}
                    )
                    st.success("建议生成完毕")
                    st.markdown(recommendations)
                except Exception as e:
                    st.error(f"建议生成失败: {e}")


if __name__ == "__main__":
    main()
