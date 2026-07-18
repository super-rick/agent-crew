"""Reusable UI components for the Dashboard.

Plotly charts and Streamlit widgets shared across pages.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Colour Palette ──────────────────────────────────────────

COLORS = {
    "success": "#16a34a",
    "fail": "#dc2626",
    "primary": "#3b82f6",
    "secondary": "#6366f1",
    "muted": "#6b7280",
    "bg": "#f8fafc",
}

PLATFORM_COLORS = {
    "juejin": "#1e80ff",
    "zhihu": "#0066ff",
    "twitter": "#1da1f2",
}


# ── Metric Cards ──────────────────────────────────────────


def metric_cards(metrics: dict) -> None:
    """Display a row of KPI metric cards.

    Expected keys: total_posts, success_rate, platform_count, active_days
    """
    cols = st.columns(4)
    cards = [
        ("📝 总发布数", metrics.get("total_posts", 0), None),
        ("✅ 成功率", f"{metrics.get('success_rate', 0):.1f}%", None),
        ("🌐 覆盖平台", metrics.get("platform_count", 0), None),
        ("📅 活跃天数", metrics.get("active_days", 0), None),
    ]
    for col, (label, value, _delta) in zip(cols, cards):
        with col:
            st.metric(label=label, value=value)


# ── Post History Table ──────────────────────────────────────


def post_history_table(records: list[dict], limit: int = 20) -> None:
    """Render a styled table of recent posts."""
    if not records:
        st.info("暂无发布记录。去 CLI 发布一篇内容吧！")
        return

    rows = []
    for r in records[-limit:]:
        rows.append(
            {
                "时间": _fmt_time(r.get("posted_at", "")),
                "平台": r.get("platform", "?"),
                "标题": (r.get("title") or r.get("post_id") or "-")[:40],
                "状态": "✅" if r.get("success") else "❌",
                "链接": r.get("post_url", "") if r.get("success") else r.get("error_message", ""),
            }
        )

    df = pd.DataFrame(rows)

    def _color_status(val):
        return [
            "background-color: #dcfce7" if v == "✅" else "background-color: #fee2e2" for v in val
        ]

    styled = df.style.apply(_color_status, subset=["状态"])
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ── Charts ──────────────────────────────────────────────────


def platform_bar_chart(platform_stats: list[dict]) -> None:
    """Horizontal stacked bar: success vs fail per platform."""
    if not platform_stats:
        st.info("暂无平台数据。")
        return

    df = pd.DataFrame(platform_stats)
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["platform"],
            x=df["success"],
            name="成功",
            orientation="h",
            marker_color=COLORS["success"],
            text=df["success"],
            textposition="inside",
        )
    )
    fig.add_trace(
        go.Bar(
            y=df["platform"],
            x=df["fail"],
            name="失败",
            orientation="h",
            marker_color=COLORS["fail"],
            text=df["fail"],
            textposition="inside",
        )
    )
    fig.update_layout(
        barmode="stack",
        title="各平台发布统计",
        xaxis_title="发布数",
        height=200 + 40 * len(platform_stats),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)


def daily_line_chart(daily_counts: list[dict]) -> None:
    """Line chart showing daily post trend."""
    if not daily_counts:
        st.info("暂无日维度数据。")
        return

    df = pd.DataFrame(daily_counts)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["total"],
            mode="lines+markers",
            name="发布数",
            line=dict(color=COLORS["primary"], width=2),
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.1)",
        )
    )
    fig.update_layout(
        title="每日发布趋势",
        xaxis_title="日期",
        yaxis_title="发布数",
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def success_rate_chart(platform_stats: list[dict]) -> None:
    """Pie charts: success rate per platform."""
    if not platform_stats:
        st.info("暂无平台数据。")
        return

    cols = st.columns(min(len(platform_stats), 3))
    for i, p in enumerate(platform_stats):
        with cols[i % 3]:
            color = PLATFORM_COLORS.get(p["platform"], COLORS["primary"])
            fig = go.Figure(
                go.Pie(
                    labels=["成功", "失败"],
                    values=[p["success"], p["fail"]],
                    hole=0.5,
                    marker_colors=[color, COLORS["muted"]],
                )
            )
            fig.update_layout(
                title=f"{p['platform']} ({p['success_rate']}%)",
                height=250,
                margin=dict(l=10, r=10, t=40, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)


def platform_breakdown_chart(platform_stats: list[dict]) -> None:
    """Treemap showing platform distribution."""
    if not platform_stats:
        st.info("暂无平台数据。")
        return

    df = pd.DataFrame(platform_stats)
    fig = px.treemap(
        df,
        path=["platform"],
        values="total",
        color="success_rate",
        color_continuous_scale="RdYlGn",
        title="平台发布占比",
    )
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)


# ── Error Panel ─────────────────────────────────────────────


def error_panel(failures: list[dict]) -> None:
    """Display a list of recent failures."""
    if not failures:
        st.success("🎉 近期无失败记录！")
        return

    st.warning(f"近期有 {len(failures)} 条失败记录")
    for f in failures:
        st.markdown(
            f"- **{f.get('platform', '?')}** | {_fmt_time(f.get('posted_at', ''))} | "
            f"`{f.get('error', '未知错误')}`"
        )


# ── Helpers ─────────────────────────────────────────────────


def _fmt_time(s: str) -> str:
    """Format ISO time to readable local time."""
    if not s:
        return "-"
    try:
        dt = pd.Timestamp(s)
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        return s[:16]  # fallback: truncate


def show_empty_state(message: str = "暂无数据。") -> None:
    """Display a friendly empty-state message."""
    st.markdown(
        f"<p style='color:#6b7280;text-align:center;padding:2rem 0;'>{message}</p>",
        unsafe_allow_html=True,
    )
