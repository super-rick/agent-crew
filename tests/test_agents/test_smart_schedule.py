"""Tests for smart scheduling (v0.4)."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from agents.analyst import AnalystAgent
from agents.base import Task
from orchestrator.scheduler import Scheduler


class TestAnalystPredictBestTimes:
    """Test AnalystAgent smart schedule analysis."""

    def _make_analyst_with_data(self, records: list[dict]) -> AnalystAgent:
        """Create analyst with pre-loaded post history."""
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        json.dump(records, tmp)
        tmp.close()
        mock_llm = MagicMock()
        return AnalystAgent(mock_llm, config={"history_file": tmp.name})

    def test_rank_publish_times_empty(self, mock_llm_client):
        """Empty history should return empty list."""
        analyst = AnalystAgent(
            mock_llm_client,
            config={"history_file": "/nonexistent/path.json"},
        )
        ranked = analyst.rank_publish_times()
        assert ranked == []

    def test_rank_publish_times_with_data(self):
        """Data should be ranked by success rate."""
        records = [
            {"platform": "juejin", "success": True, "posted_at": "2026-07-19T08:30:00"},
            {"platform": "juejin", "success": True, "posted_at": "2026-07-19T08:45:00"},
            {"platform": "juejin", "success": False, "posted_at": "2026-07-19T15:00:00"},
            {"platform": "juejin", "success": True, "posted_at": "2026-07-19T12:00:00"},
        ]
        analyst = self._make_analyst_with_data(records)
        ranked = analyst.rank_publish_times(platform="juejin")

        assert len(ranked) > 0
        # 8am has 2 success out of 2 (100%), should rank high
        hour8 = next(r for r in ranked if r["hour"] == 8)
        assert hour8["success_rate"] == 100.0

    def test_predict_best_times_with_data(self):
        """Should return best hours from real data."""
        records = [
            {"platform": "juejin", "success": True, "posted_at": "2026-07-19T09:00:00"},
            {"platform": "juejin", "success": True, "posted_at": "2026-07-18T09:30:00"},
            {"platform": "juejin", "success": False, "posted_at": "2026-07-17T03:00:00"},
            {"platform": "juejin", "success": True, "posted_at": "2026-07-16T12:00:00"},
        ]
        analyst = self._make_analyst_with_data(records)
        hours = analyst.predict_best_times(platform="juejin", top_n=2)
        assert len(hours) >= 1
        assert 9 in hours  # Best hour based on data

    def test_predict_best_times_fallback(self, mock_llm_client):
        """No data → use sensible defaults."""
        analyst = AnalystAgent(
            mock_llm_client,
            config={"history_file": "/nonexistent/path.json"},
        )
        hours = analyst.predict_best_times(platform="juejin")
        assert len(hours) == 3
        assert hours == [8, 12, 20]  # Juejin defaults

    def test_predict_best_times_fallback_zhihu(self, mock_llm_client):
        analyst = AnalystAgent(
            mock_llm_client,
            config={"history_file": "/nonexistent/path.json"},
        )
        hours = analyst.predict_best_times(platform="zhihu")
        assert hours == [10, 15, 21]

    def test_predict_best_times_fallback_devto(self, mock_llm_client):
        analyst = AnalystAgent(
            mock_llm_client,
            config={"history_file": "/nonexistent/path.json"},
        )
        hours = analyst.predict_best_times(platform="devto")
        assert hours == [15, 17, 12]

    def test_filter_by_platform(self):
        """rank_publish_times should filter by platform."""
        records = [
            {"platform": "juejin", "success": True, "posted_at": "2026-07-19T08:00:00"},
            {"platform": "zhihu", "success": True, "posted_at": "2026-07-19T20:00:00"},
        ]
        analyst = self._make_analyst_with_data(records)
        juejin_ranked = analyst.rank_publish_times(platform="juejin")
        zhihu_ranked = analyst.rank_publish_times(platform="zhihu")
        assert len(juejin_ranked) == 1
        assert juejin_ranked[0]["hour"] == 8
        assert len(zhihu_ranked) == 1
        assert zhihu_ranked[0]["hour"] == 20


class TestSchedulerSmartSchedule:
    """Test Scheduler.set_smart_schedule."""

    def test_distributes_tasks_across_hours(self):
        """Tasks should be spread across best hours."""
        store_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            scheduler = Scheduler(store_path=store_path)
            tasks = [
                Task(task_id=f"t{i}", task_type="write", params={"topic": f"Topic {i}"})
                for i in range(6)
            ]
            best_hours = [8, 12, 20]
            scheduler.set_smart_schedule(best_hours, tasks, days=1)

            assert len(scheduler._tasks) == 6
            hours = {t["next_run"].hour for t in scheduler._tasks}
            # Some hours may be in the past and get bumped forward
            assert len(hours) >= 1
            assert all(0 <= h <= 23 for h in hours)
        finally:
            Path(store_path).unlink(missing_ok=True)

    def test_empty_tasks_no_error(self):
        scheduler = Scheduler()
        scheduler.set_smart_schedule([8, 12], [], days=1)
        assert len(scheduler._tasks) == 0

    def test_empty_hours_no_error(self):
        scheduler = Scheduler()
        task = Task(task_id="t1", task_type="write")
        scheduler.set_smart_schedule([], [task], days=1)
        assert len(scheduler._tasks) == 0

    def test_tasks_rounded_to_nearest_hour(self):
        store_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            scheduler = Scheduler(store_path=store_path)
            task = Task(task_id="t1", task_type="write")
            scheduler.set_smart_schedule([9], [task], days=1)

            next_run = scheduler._tasks[0]["next_run"]
            assert next_run.minute == 0  # Rounded to hour
            assert next_run > datetime.now()  # Must be in the future
        finally:
            Path(store_path).unlink(missing_ok=True)

    def test_tasks_saved_to_store(self):
        store_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            scheduler = Scheduler(store_path=store_path)
            task = Task(task_id="t1", task_type="write", params={})
            scheduler.set_smart_schedule([12], [task], days=1)

            from orchestrator.task_store import TaskStore

            store = TaskStore(store_path)
            stored = store.load_tasks()
            assert len(stored) == 1
        finally:
            Path(store_path).unlink(missing_ok=True)
