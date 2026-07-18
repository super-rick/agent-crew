"""Publishing analysis page — platform breakdown, daily trends, failures."""

from __future__ import annotations

import streamlit as st

from agents.analyst import AnalystAgent
from dashboard.components import (
    daily_line_chart,
    error_panel,
    platform_bar_chart,
    platform_breakdown_chart,
    post_history_table,
    success_rate_chart,
)
from dashboard.data_loader import load_post_history


def _get_metrics(records: list[dict], days: int = 30) -> dict:
    """Use AnalystAgent's metrics calculator (no LLM needed)."""
    agent = AnalystAgent.__new__(AnalystAgent)
    agent._history_file = ""  # not used — we pass filtered data directly
    agent._default_days = days
    return agent._calculate_metrics(records, days)


def main() -> None:
    st.title("📊 发布分析")
    st.caption("各平台发布表现、日趋势和失败记录")

    records = load_post_history()
    if not records:
        st.info("暂无发布记录。去 CLI 试试 `agentcrew-mcnpublish post --help`！")
        return

    # ── Filters ──
    col1, col2 = st.columns(2)
    with col1:
        days = st.slider("统计天数", min_value=1, max_value=90, value=30, step=1)
    with col2:
        platforms = sorted({r.get("platform", "?") for r in records})
        selected_platforms = st.multiselect("按平台筛选", platforms, default=platforms)

    filtered = [r for r in records if r.get("platform") in selected_platforms]
    # Also filter by days
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(days=days)
    filtered = [r for r in filtered if r.get("posted_at") and _in_range(r["posted_at"], cutoff)]

    if not filtered:
        st.info("当前筛选条件下无数据。")
        return

    metrics = _get_metrics(filtered, days)

    # ── Summary Row ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📝 总发布", metrics["total_posts"])
    c2.metric("✅ 成功", metrics["success_count"])
    c3.metric("❌ 失败", metrics["fail_count"])
    c4.metric("📈 成功率", f"{metrics['success_rate']:.1f}%")

    # ── Charts ──
    st.subheader("各平台表现")
    tab1, tab2, tab3 = st.tabs(["柱状图", "成功率", "占比"])

    with tab1:
        platform_bar_chart(metrics.get("platform_stats", []))
    with tab2:
        success_rate_chart(metrics.get("platform_stats", []))
    with tab3:
        platform_breakdown_chart(metrics.get("platform_stats", []))

    # ── Daily Trend ──
    st.subheader("发布趋势")
    daily_line_chart(metrics.get("daily_counts", []))

    # ── Failures ──
    st.subheader("失败记录")
    error_panel(metrics.get("recent_fails", []))

    # ── Full History Table ──
    st.subheader("发布历史")
    post_history_table(filtered)


def _in_range(posted_at: str, cutoff) -> bool:
    """Check if a posted_at ISO string is >= cutoff."""
    try:
        from datetime import datetime as dt

        return dt.fromisoformat(posted_at) >= cutoff
    except Exception:
        return True  # include if unparseable


if __name__ == "__main__":
    main()
