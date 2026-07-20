"""AgentCrew MCN Dashboard — Streamlit web UI (EN default, ZH toggle)."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from dashboard.data_loader import get_data_freshness, has_api_key, load_post_history  # noqa: E402
from dashboard.i18n import get_lang, init_language, set_lang, t  # noqa: E402

st.set_page_config(
    page_title="AgentCrew MCN Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_language()

# ── Navigation ──────────────────────────────────────────────

_PAGE_LABELS = {
    "en": {
        "overview": "Overview",
        "publishing": "Publishing",
        "analytics": "AI Analytics",
        "system": "System",
    },
    "zh": {
        "overview": "总览",
        "publishing": "发布分析",
        "analytics": "AI 分析",
        "system": "系统状态",
    },
}


def _render_overview() -> None:
    st.title(f"🤖 {t('title')}")
    st.caption(t("subtitle"))

    records = load_post_history()
    total = len(records)
    success_count = sum(1 for r in records if r.get("success"))
    rate = (success_count / total * 100) if total else 0.0
    platforms = len({r.get("platform") for r in records})
    active_days = len({r.get("posted_at", "")[:10] for r in records if r.get("posted_at")})

    st.subheader(t("core_metrics"))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"📝 {t('total_posts')}", total)
    c2.metric(f"✅ {t('success_rate')}", f"{rate:.1f}%")
    c3.metric(f"🌐 {t('platforms')}", platforms)
    c4.metric(f"📅 {t('active_days')}", active_days)

    st.divider()
    st.subheader(t("system_status"))
    status_cols = st.columns(4)
    api_ok = has_api_key()
    status_cols[0].markdown(
        f"{'✅' if api_ok else '❌'} **{t('llm_api')}** — "
        f"{t('configured') if api_ok else t('not_configured')}"
    )
    status_cols[1].markdown(f"📂 **{t('data_file')}** — {t('exists') if records else t('no_data')}")
    freshness = get_data_freshness()
    status_cols[2].markdown(f"🕐 **{t('data_update')}** — {freshness or t('none')}")
    status_cols[3].markdown(f"🤖 **{t('ai_employees')}** — Writer, Reviewer, Publisher, Analyst")

    st.divider()

    st.subheader(f"📋 {t('recent_posts')}")
    if records:
        from dashboard.components import post_history_table

        post_history_table(records, limit=10)

        st.subheader(f"📊 {t('platform_distribution')}")
        from agents.analyst import AnalystAgent

        agent = AnalystAgent.__new__(AnalystAgent)
        agent._history_file = ""
        agent._default_days = 30
        metrics = agent._calculate_metrics(records, 30)

        c1, c2 = st.columns(2)
        with c1:
            from dashboard.components import platform_bar_chart

            platform_bar_chart(metrics.get("platform_stats", []))
        with c2:
            from dashboard.components import daily_line_chart

            daily_line_chart(metrics.get("daily_counts", []))

        st.divider()
        st.subheader(f"📈 {t('growth_metrics')}")
        gc = st.columns(4)
        gc[0].metric(f"⭐ {t('github_stars')}", "2", delta=t("v_released"))
        gc[1].metric(f"📦 {t('pypi_version')}", "v0.5.1")
        gc[2].metric(f"🧪 {t('test_coverage')}", "392 tests")
        gc[3].metric(f"🤖 {t('ai_agents')}", "4 Agents", delta=t("plus_reviewer"))
        st.caption(
            f"[{t('growth_source')}](https://github.com/super-rick/agentcrew-mcn/blob/main/GROWTH.md)"
        )

    else:
        st.info(
            f"👋 {t('welcome_title')}\n\n"
            f"{t('welcome_text')}\n\n"
            "```bash\n"
            'agentcrew-mcn write generate --topic "Python AI Agent" --style technical\n'
            'agentcrew-mcn publish post --text "Content..." --platform juejin --dry-run\n'
            "```"
        )


# ── Sidebar ─────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"## 🤖 {t('sidebar_title')}")
    st.markdown(f"*{t('sidebar_subtitle')}*")

    # Language selector
    lang = st.selectbox(
        t("language"),
        options=["en", "zh"],
        format_func=lambda x: "🇺🇸 English" if x == "en" else "🇨🇳 中文",
        index=0 if get_lang() == "en" else 1,
    )
    if lang != get_lang():
        set_lang(lang)
        st.rerun()

    st.divider()

    records = load_post_history()
    total = len(records)
    success = sum(1 for r in records if r.get("success"))
    st.metric(t("total_posts"), total)
    st.metric(t("success_rate").replace("率", "").replace("Success Rate", "Success"), success)
    if total:
        st.progress(success / total, text=f"{t('success_rate')} {success/total*100:.0f}%")

    st.divider()

    # Navigation
    labels = _PAGE_LABELS[get_lang()]
    page = st.radio("", list(labels.values()), label_visibility="collapsed")

    st.divider()
    st.caption("AgentCrew MCN v0.5.0 | [GitHub](https://github.com/super-rick/agentcrew-mcn)")

# ── Page Router ─────────────────────────────────────────────

_page_map = {v: k for k, v in _PAGE_LABELS[get_lang()].items()}
page_key = _page_map.get(page, "overview")

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
