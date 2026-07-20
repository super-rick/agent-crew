"""Dashboard i18n — English default, Chinese toggle."""

from __future__ import annotations

import streamlit as st

TRANSLATIONS = {
    "en": {
        "title": "AgentCrew MCN Dashboard",
        "subtitle": "AI Marketing Automation — Your AI team works 24/7",
        "core_metrics": "Core Metrics",
        "total_posts": "Total Posts",
        "success_rate": "Success Rate",
        "platforms": "Platforms",
        "active_days": "Active Days",
        "system_status": "System Status",
        "llm_api": "LLM API",
        "configured": "Configured",
        "not_configured": "Not configured — set DEEPSEEK_API_KEY",
        "data_file": "Data File",
        "exists": "Exists",
        "no_data": "No Data",
        "data_update": "Data Update",
        "ai_employees": "AI Employees",
        "recent_posts": "Recent Posts",
        "platform_distribution": "Platform Distribution",
        "growth_metrics": "Growth Metrics",
        "github_stars": "GitHub Stars",
        "pypi_version": "PyPI Version",
        "test_coverage": "Test Coverage",
        "ai_agents": "AI Agents",
        "growth_source": "Data source: GROWTH.md",
        "welcome_title": "Welcome to AgentCrew!",
        "welcome_text": "No posts yet. Get started from CLI:",
        "nav_overview": "Overview",
        "nav_publishing": "Publishing",
        "nav_analytics": "AI Analytics",
        "nav_system": "System",
        "sidebar_title": "AgentCrew",
        "sidebar_subtitle": "AI MCN Automation",
        "quick_summary": "Quick Summary",
        "none": "N/A",
        "language": "Language",
        "v_released": "v0.5.1 released",
        "plus_reviewer": "+1 Reviewer",
    },
    "zh": {
        "title": "AgentCrew MCN Dashboard",
        "subtitle": "AI MCN 自动推广工具 — 你的 AI 营销团队，24 小时在线",
        "core_metrics": "核心指标",
        "total_posts": "总发布数",
        "success_rate": "成功率",
        "platforms": "覆盖平台",
        "active_days": "活跃天数",
        "system_status": "系统状态",
        "llm_api": "LLM API",
        "configured": "已配置",
        "not_configured": "未配置 — 请设 DEEPSEEK_API_KEY",
        "data_file": "数据文件",
        "exists": "存在",
        "no_data": "暂无数据",
        "data_update": "数据更新",
        "ai_employees": "AI 员工",
        "recent_posts": "最近发布",
        "platform_distribution": "平台分布",
        "growth_metrics": "增长指标 (Growth)",
        "github_stars": "GitHub Stars",
        "pypi_version": "PyPI 版本",
        "test_coverage": "测试覆盖",
        "ai_agents": "AI 员工",
        "growth_source": "数据来源: GROWTH.md",
        "welcome_title": "欢迎使用 AgentCrew！",
        "welcome_text": "还没有发布记录。试试从 CLI 开始：",
        "nav_overview": "总览",
        "nav_publishing": "发布分析",
        "nav_analytics": "AI 分析",
        "nav_system": "系统状态",
        "sidebar_title": "AgentCrew",
        "sidebar_subtitle": "AI MCN 自动推广工具",
        "quick_summary": "快速概况",
        "none": "无",
        "language": "语言",
        "v_released": "v0.5.1 发布",
        "plus_reviewer": "+1 Reviewer",
    },
}


def init_language() -> None:
    """Initialize language from session state, default English."""
    if "lang" not in st.session_state:
        st.session_state.lang = "en"


def get_lang() -> str:
    return st.session_state.get("lang", "en")


def set_lang(lang: str) -> None:
    st.session_state.lang = lang


def t(key: str) -> str:
    """Translate a key to the current language."""
    lang = get_lang()
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
