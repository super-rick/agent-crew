"""Tests for the Analyst Agent."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from agents.analyst import AnalystAgent
from agents.base import Task


def _make_post_record(
    platform: str = "juejin",
    success: bool = True,
    error_message: str | None = None,
    days_ago: int = 1,
    post_id: str | None = "post_001",
) -> dict:
    """Helper to build a sample post history record."""
    posted_at = (datetime.now() - timedelta(days=days_ago)).isoformat()
    return {
        "success": success,
        "platform": platform,
        "post_id": post_id,
        "post_url": f"https://{platform}.example.com/{post_id}" if post_id else None,
        "error_message": error_message,
        "posted_at": posted_at,
        "metrics": {},
    }


class TestAnalystAgent:
    """Test suite for AnalystAgent."""

    # ── Initialization ──────────────────────────────────

    def test_initialization(self, mock_llm_client):
        """Agent should initialize with correct name and description."""
        agent = AnalystAgent(mock_llm_client)
        assert agent.name == "analyst"
        assert agent.description is not None

    def test_initialization_with_config(self, mock_llm_client):
        """Agent should accept config for history_file and default_days."""
        agent = AnalystAgent(
            mock_llm_client,
            config={"history_file": "custom/path.json", "default_days": 14},
        )
        assert agent._history_file == "custom/path.json"
        assert agent._default_days == 14

    def test_initialization_defaults(self, mock_llm_client):
        """Agent should use sensible defaults without config."""
        agent = AnalystAgent(mock_llm_client)
        assert agent._history_file == "data/post_history.json"
        assert agent._default_days == 7

    def test_get_system_prompt(self, mock_llm_client):
        """System prompt should describe the analyst role."""
        agent = AnalystAgent(mock_llm_client)
        prompt = agent.get_system_prompt()
        assert prompt is not None
        assert len(prompt) > 0
        assert "数据分析" in prompt or "分析师" in prompt

    # ── Analyze (data aggregation, no LLM) ──────────────

    def test_analyze_empty_history(self, mock_llm_client):
        """Analyze with no history should return zero counts."""
        agent = AnalystAgent(mock_llm_client)

        with patch.object(agent, "_load_history", return_value=[]):
            task = Task(
                task_id="test_001",
                task_type="analyst",
                params={"action": "analyze", "days": 7},
            )
            result = agent.execute(task)

        assert result.success
        assert result.data["total_posts"] == 0
        assert result.data["success_count"] == 0
        assert result.data["fail_count"] == 0
        assert result.data["platform_stats"] == []

    def test_analyze_with_data(self, mock_llm_client):
        """Analyze should aggregate post history correctly."""
        records = [
            _make_post_record("juejin", True, days_ago=1),
            _make_post_record("juejin", True, days_ago=2),
            _make_post_record("zhihu", True, days_ago=3),
            _make_post_record("zhihu", False, "Auth failed", days_ago=1),
        ]
        agent = AnalystAgent(mock_llm_client)

        with patch.object(agent, "_load_history", return_value=records):
            task = Task(
                task_id="test_002",
                task_type="analyst",
                params={"action": "analyze", "days": 7},
            )
            result = agent.execute(task)

        assert result.success
        assert result.data["total_posts"] == 4
        assert result.data["success_count"] == 3
        assert result.data["fail_count"] == 1
        assert result.data["success_rate"] == 75.0

        # Platform stats
        stats = {s["platform"]: s for s in result.data["platform_stats"]}
        assert stats["juejin"]["total"] == 2
        assert stats["juejin"]["success"] == 2
        assert stats["juejin"]["success_rate"] == 100.0
        assert stats["zhihu"]["total"] == 2
        assert stats["zhihu"]["success"] == 1
        assert stats["zhihu"]["success_rate"] == 50.0

    def test_analyze_respects_days_filter(self, mock_llm_client):
        """Analyze should only include records within the specified days."""
        records = [
            _make_post_record("juejin", True, days_ago=1),
            _make_post_record("juejin", True, days_ago=10),  # outside 7-day window
        ]
        agent = AnalystAgent(mock_llm_client)

        with patch.object(agent, "_load_history", return_value=records):
            task = Task(
                task_id="test_003",
                task_type="analyst",
                params={"action": "analyze", "days": 7},
            )
            result = agent.execute(task)

        assert result.data["total_posts"] == 1

    def test_analyze_with_platform_filter(self, mock_llm_client):
        """Analyze should filter by platform when specified."""
        records = [
            _make_post_record("juejin", True, days_ago=1),
            _make_post_record("zhihu", True, days_ago=1),
        ]
        agent = AnalystAgent(mock_llm_client)

        with patch.object(agent, "_load_history", return_value=records):
            task = Task(
                task_id="test_004",
                task_type="analyst",
                params={"action": "analyze", "days": 7, "platforms": ["juejin"]},
            )
            result = agent.execute(task)

        assert result.data["total_posts"] == 1
        assert result.data["platform_stats"][0]["platform"] == "juejin"

    # ── Report (LLM-powered) ────────────────────────────

    def test_report_calls_llm(self, mock_llm_client):
        """Report should invoke LLM and include report text in result."""
        records = [
            _make_post_record("juejin", True, days_ago=1),
            _make_post_record("zhihu", False, "API Error", days_ago=2),
        ]
        agent = AnalystAgent(mock_llm_client)

        with patch.object(agent, "_load_history", return_value=records):
            task = Task(
                task_id="test_005",
                task_type="analyst",
                params={"action": "report", "days": 7},
            )
            result = agent.execute(task)

        assert result.success
        mock_llm_client.chat.assert_called_once()
        assert result.data["report"] is not None
        assert "测试生成" in result.data["report"]

    def test_report_includes_metrics(self, mock_llm_client):
        """Report result should include both report text and metrics data."""
        records = [_make_post_record("juejin", True, days_ago=1)]
        agent = AnalystAgent(mock_llm_client)

        with patch.object(agent, "_load_history", return_value=records):
            task = Task(
                task_id="test_006",
                task_type="analyst",
                params={"action": "report", "days": 7},
            )
            result = agent.execute(task)

        assert "report" in result.data
        assert "total_posts" in result.data
        assert result.data["total_posts"] == 1

    # ── Recommend (LLM-powered) ─────────────────────────

    def test_recommend_calls_llm(self, mock_llm_client):
        """Recommend should invoke LLM and include recommendation text."""
        records = [_make_post_record("juejin", True, days_ago=1)]
        agent = AnalystAgent(mock_llm_client)

        with patch.object(agent, "_load_history", return_value=records):
            task = Task(
                task_id="test_007",
                task_type="analyst",
                params={"action": "recommend", "days": 14},
            )
            result = agent.execute(task)

        assert result.success
        assert result.data["recommendations"] is not None

    # ── Error handling ─────────────────────────────────

    def test_default_action_is_analyze(self, mock_llm_client):
        """If no action is specified, default to analyze."""
        agent = AnalystAgent(mock_llm_client)

        with patch.object(agent, "_load_history", return_value=[]):
            task = Task(
                task_id="test_008",
                task_type="analyst",
                params={"days": 7},
            )
            result = agent.execute(task)

        assert result.success
        assert result.data["action"] == "analyze"

    def test_unknown_action_returns_error(self, mock_llm_client):
        """Unknown action should return failure."""
        agent = AnalystAgent(mock_llm_client)
        task = Task(
            task_id="test_009",
            task_type="analyst",
            params={"action": "invalid_action"},
        )
        result = agent.execute(task)
        assert not result.success
        assert "Unknown action" in (result.error_message or "")

    def test_llm_failure_reported(self):
        """If LLM client throws on report, the analyst should capture it."""
        failing_client = MagicMock()
        failing_client.chat.side_effect = Exception("API Error")

        agent = AnalystAgent(failing_client)
        task = Task(
            task_id="test_010",
            task_type="analyst",
            params={"action": "report", "days": 7},
        )
        result = agent.execute(task)
        assert not result.success
        assert "API Error" in (result.error_message or "")

    def test_missing_history_file(self, mock_llm_client):
        """When history file doesn't exist, _load_history returns empty list."""
        agent = AnalystAgent(
            mock_llm_client,
            config={"history_file": "/nonexistent/path.json"},
        )
        assert agent._load_history() == []

    # ── Internal helpers ────────────────────────────────

    def test_calculate_metrics_daily_counts(self, mock_llm_client):
        """_calculate_metrics should produce correct daily breakdown."""
        records = [
            _make_post_record("juejin", True, days_ago=0),
            _make_post_record("juejin", True, days_ago=1),
        ]
        agent = AnalystAgent(mock_llm_client)
        metrics = agent._calculate_metrics(records, days=3)

        assert metrics["total_posts"] == 2
        assert len(metrics["daily_counts"]) == 3  # 3 days, zero-filled
        assert any(d["total"] > 0 for d in metrics["daily_counts"])

    def test_filter_by_days(self, mock_llm_client):
        """_filter_by_days should only keep records within the window."""
        records = [
            _make_post_record("juejin", True, days_ago=1),
            _make_post_record("juejin", True, days_ago=30),
        ]
        filtered = AnalystAgent._filter_by_days(records, days=7)
        assert len(filtered) == 1

    def test_filter_by_days_empty(self, mock_llm_client):
        """_filter_by_days should handle empty input."""
        assert AnalystAgent._filter_by_days([], days=7) == []

    def test_filter_by_days_missing_timestamp(self, mock_llm_client):
        """_filter_by_days should skip records without posted_at."""
        records = [
            {"success": True, "platform": "juejin"},  # no posted_at
            _make_post_record("juejin", True, days_ago=1),
        ]
        filtered = AnalystAgent._filter_by_days(records, days=7)
        assert len(filtered) == 1

    def test_error_summary(self, mock_llm_client):
        """Error summary should group similar errors."""
        records = [
            _make_post_record("zhihu", False, "Auth failed: token expired", days_ago=1),
            _make_post_record("zhihu", False, "Auth failed: invalid cookie", days_ago=2),
            _make_post_record("juejin", False, "Rate limit exceeded", days_ago=1),
        ]
        agent = AnalystAgent(mock_llm_client)
        metrics = agent._calculate_metrics(records, days=7)

        assert metrics["fail_count"] == 3
        assert "Auth failed" in metrics["error_summary"]
        assert metrics["error_summary"]["Auth failed"] == 2
        assert metrics["error_summary"]["Rate limit exceeded"] == 1

    def test_recent_fails_at_most_five(self, mock_llm_client):
        """Recent fails should keep at most 5 records."""
        records = [_make_post_record("juejin", False, f"error {i}", days_ago=i) for i in range(10)]
        agent = AnalystAgent(mock_llm_client)
        metrics = agent._calculate_metrics(records, days=14)
        assert len(metrics["recent_fails"]) <= 5
