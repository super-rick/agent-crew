"""AgentCrew MCN Dashboard — Streamlit web UI.

Usage:
    streamlit run dashboard/app.py

Pages:
    - 总览 (Overview) — KPIs, recent posts, platform breakdown
    - 发布分析 (Publishing) — detailed charts and filtering
    - AI 分析 (Analytics) — AI-generated reports and recommendations
    - 系统状态 (System) — connections, RAG, config, logs
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on the Python path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from dashboard.data_loader import (  # noqa: E402
    get_data_freshness,
    has_api_key,
    load_post_history,
)

st.set_page_config(
    page_title="AgentCrew MCN Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Navigation ──────────────────────────────────────────────

PAGES = {
    "📈 总览": "overview",
    "📊 发布分析": "publishing",
    "🤖 AI 分析": "analytics",
    "⚙️ 系统状态": "system",
}


def _render_overview() -> None:
    """Render the Overview (home) page."""
    st.title("🤖 AgentCrew MCN Dashboard")
    st.caption("AI MCN 自动推广工具 — 你的 AI 营销团队，24 小时在线")

    records = load_post_history()

    # ── Quick Stats ──
    total = len(records)
    success_count = sum(1 for r in records if r.get("success"))
    _fail_count = total - success_count  # noqa: F841
    rate = (success_count / total * 100) if total else 0.0
    platforms = len({r.get("platform") for r in records})
    # Active days = distinct dates with posts
    active_days = len({r.get("posted_at", "")[:10] for r in records if r.get("posted_at")})

    st.subheader("核心指标")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📝 总发布数", total)
    c2.metric("✅ 成功率", f"{rate:.1f}%")
    c3.metric("🌐 覆盖平台", platforms)
    c4.metric("📅 活跃天数", active_days)

    # ── System Status Bar ──
    st.divider()
    status_cols = st.columns(4)
    api_ok = has_api_key()
    status_cols[0].markdown(
        f"{'✅' if api_ok else '❌'} **LLM API** — "
        f"{'已配置' if api_ok else '未配置 — 请设 DEEPSEEK_API_KEY'}"
    )
    status_cols[1].markdown(f"📂 **数据文件** — {'存在' if records else '暂无数据'}")
    freshness = get_data_freshness()
    status_cols[2].markdown(f"🕐 **数据更新** — {freshness or 'N/A'}")
    status_cols[3].markdown("🤖 **AI 员工** — Writer, Publisher, Analyst")

    st.divider()

    # ── Recent Posts ──
    st.subheader("📋 最近发布")
    if records:
        from dashboard.components import post_history_table

        post_history_table(records, limit=10)

        # ── Quick Chart ──
        st.subheader("📊 平台分布")
        from agents.analyst import AnalystAgent

        agent = AnalystAgent.__new__(AnalystAgent)
        agent._history_file = ""
        agent._default_days = 30
        metrics = agent._calculate_metrics(records, 30)

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            from dashboard.components import platform_bar_chart

            platform_bar_chart(metrics.get("platform_stats", []))
        with chart_col2:
            from dashboard.components import daily_line_chart

            daily_line_chart(metrics.get("daily_counts", []))

        # ── Growth Metrics ──
        st.divider()
        st.subheader("📈 增长指标 (Growth)")
        growth_cols = st.columns(4)
        growth_cols[0].metric("⭐ GitHub Stars", "1", delta="v0.3.0 发布")
        growth_cols[1].metric("📦 PyPI 版本", "v0.3.0")
        growth_cols[2].metric("🧪 测试覆盖", "317 tests")
        growth_cols[3].metric("🤖 AI 员工", "4 Agents", delta="+1 Reviewer")
        st.caption(
            "数据来源: [GROWTH.md](https://github.com/super-rick/agentcrew-mcn/blob/main/GROWTH.md)"
        )

    else:
        st.info(
            "👋 欢迎使用 AgentCrew！\n\n"
            "还没有发布记录。试试从 CLI 开始：\n\n"
            "```bash\n"
            "# 生成一篇内容\n"
            'agentcrew-mcnwrite generate --topic "Python AI Agent 入门" --style technical\n\n'
            "# 发布到掘金（预览模式）\n"
            'agentcrew-mcnpublish post --text "内容..." --platform juejin --dry-run\n'
            "```"
        )


# ── Sidebar ─────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🤖 AgentCrew")
    st.markdown("*AI MCN 自动推广工具*")

    # Navigation
    page = st.radio("导航", list(PAGES.keys()), label_visibility="collapsed")

    st.divider()

    # Quick summary in sidebar
    records = load_post_history()
    total = len(records)
    success = sum(1 for r in records if r.get("success"))
    st.metric("总发布", total)
    st.metric("成功", success)
    if total:
        st.progress(success / total, text=f"成功率 {success/total*100:.0f}%")

    st.divider()
    st.caption("AgentCrew MCN v0.2.0 | [GitHub](https://github.com)")

# ── Page Router ─────────────────────────────────────────────

page_key = PAGES.get(page, "overview")

if page_key == "overview":
    _render_overview()
elif page_key == "publishing":
    from dashboard.pages.publishing import main as pub_main

    pub_main()
elif page_key == "analytics":
    from dashboard.pages.analytics import main as analytics_main

    analytics_main()
elif page_key == "system":
    from dashboard.pages.system import main as sys_main

    sys_main()
