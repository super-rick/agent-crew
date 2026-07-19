"""Tests for persistent scheduler, task store, and cron parser."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from agents.base import Task
from orchestrator.scheduler import (
    Scheduler,
    is_valid_cron,
    next_cron_time,
)
from orchestrator.task_store import TaskStore


class TestCronParser:
    """Test the built-in cron expression parser."""

    def test_next_cron_daily_9am(self):
        """0 9 * * * should return 9:00 AM tomorrow if already past."""
        t = next_cron_time("0 9 * * *")
        assert t.hour == 9
        assert t.minute == 0

    def test_next_cron_weekdays(self):
        """0 9 * * 1-5 should return a weekday at 9 AM."""
        t = next_cron_time("0 9 * * 1-5")
        assert t.hour == 9
        assert t.weekday() < 5  # Monday=0, Friday=4

    def test_next_cron_specific_time(self):
        """30 14 * * * → 2:30 PM."""
        t = next_cron_time("30 14 * * *")
        assert t.hour == 14
        assert t.minute == 30

    def test_next_cron_every_6_hours(self):
        """0 */6 * * * → every 6 hours."""
        t = next_cron_time("0 */6 * * *")
        assert t.minute == 0
        assert t.hour % 6 == 0

    def test_next_cron_with_after(self):
        """next_cron_time with explicit after parameter."""
        after = datetime(2026, 7, 20, 8, 0)
        t = next_cron_time("0 9 * * *", after=after)
        assert t.day == 20
        assert t.hour == 9
        assert t.minute == 0

    def test_is_valid_cron_good(self):
        assert is_valid_cron("0 9 * * 1-5")
        assert is_valid_cron("*/5 * * * *")
        assert is_valid_cron("30 14 1 * *")
        assert is_valid_cron("0 0 1 1 *")

    def test_is_valid_cron_bad(self):
        assert not is_valid_cron("invalid")
        assert not is_valid_cron("60 9 * * *")  # minute > 59
        assert not is_valid_cron("0 24 * * *")  # hour > 23
        assert not is_valid_cron("")  # empty
        assert not is_valid_cron("* * * *")  # 4 fields

    def test_invalid_cron_raises(self):
        with pytest.raises(ValueError):
            next_cron_time("not a cron expression")


class TestTaskStore:
    """Test JSON file-based task persistence."""

    def test_save_and_load(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        try:
            store = TaskStore(tmp.name)
            store.save_task(
                schedule_id="s1",
                task_type="write_and_publish",
                task_id="t1",
                params={"topic": "Test"},
                interval_minutes=360,
                next_run=datetime(2026, 7, 20, 9, 0),
            )
            tasks = store.load_tasks()
            assert len(tasks) == 1
            assert tasks[0]["schedule_id"] == "s1"
            assert tasks[0]["interval_minutes"] == 360
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_upsert(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        try:
            store = TaskStore(tmp.name)
            store.save_task("s1", "write", "t1", {}, interval_minutes=60)
            store.save_task("s1", "write", "t1", {}, interval_minutes=120)
            tasks = store.load_tasks()
            assert len(tasks) == 1
            assert tasks[0]["interval_minutes"] == 120
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_remove(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        try:
            store = TaskStore(tmp.name)
            store.save_task("s1", "write", "t1", {}, interval_minutes=60)
            store.save_task("s2", "write", "t2", {}, interval_minutes=120)
            assert store.get_task_count() == 2
            assert store.remove_task("s1") is True
            assert store.remove_task("s1") is False  # Already removed
            assert store.get_task_count() == 1
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_clear_all(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        try:
            store = TaskStore(tmp.name)
            store.save_task("s1", "write", "t1", {})
            store.save_task("s2", "write", "t2", {})
            assert store.clear_all() == 2
            assert store.get_task_count() == 0
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_load_empty_store(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        try:
            store = TaskStore(tmp.name)
            assert store.load_tasks() == []
            assert store.get_task_count() == 0
        finally:
            Path(tmp.name).unlink(missing_ok=True)


class TestPersistentScheduler:
    """Test Scheduler with JSON persistence."""

    def test_add_recurring_saves_to_store(self):
        store_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            scheduler = Scheduler(store_path=store_path)
            task = Task(task_id="t1", task_type="write", params={})
            scheduler.add_recurring_task(task, interval_minutes=60)

            store = TaskStore(store_path)
            stored = store.load_tasks()
            assert len(stored) == 1
            assert stored[0]["task_id"] == "t1"
        finally:
            Path(store_path).unlink(missing_ok=True)

    def test_add_one_shot_saves_to_store(self):
        store_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            scheduler = Scheduler(store_path=store_path)
            task = Task(task_id="t1", task_type="write", params={})
            scheduler.add_one_shot_task(task, datetime.now() + timedelta(hours=1))

            store = TaskStore(store_path)
            stored = store.load_tasks()
            assert len(stored) == 1
            assert stored[0]["is_one_shot"] is True
        finally:
            Path(store_path).unlink(missing_ok=True)

    def test_load_from_store_restores_tasks(self):
        store_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            # First scheduler: save a task
            s1 = Scheduler(store_path=store_path)
            task = Task(task_id="t1", task_type="write", params={"topic": "Python"})
            s1.add_recurring_task(task, interval_minutes=120)

            # Second scheduler: restore
            s2 = Scheduler(store_path=store_path)
            count = s2.load_from_store()
            assert count == 1
            assert len(s2._tasks) == 1
            assert s2._tasks[0]["task"].params["topic"] == "Python"
        finally:
            Path(store_path).unlink(missing_ok=True)

    def test_cancel_removes_from_store(self):
        store_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            scheduler = Scheduler(store_path=store_path)
            task = Task(task_id="t1", task_type="write", params={})
            sid = scheduler.add_recurring_task(task, interval_minutes=60)

            store = TaskStore(store_path)
            assert store.get_task_count() == 1

            scheduler.cancel(sid)
            assert store.get_task_count() == 0
        finally:
            Path(store_path).unlink(missing_ok=True)

    def test_cron_task_scheduling(self):
        scheduler = Scheduler(
            store_path=tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        )
        task = Task(task_id="t_cron", task_type="write", params={})
        sid = scheduler.add_recurring_task(task, cron="0 9 * * 1-5")
        assert sid is not None

        entry = scheduler._tasks[0]
        assert entry["cron"] == "0 9 * * 1-5"
        assert entry["next_run"].hour == 9

    def test_due_task_auto_reschedules(self):
        store_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            scheduler = Scheduler(store_path=store_path)
            task = Task(task_id="t1", task_type="write", params={})
            scheduler.add_recurring_task(task, interval_minutes=60)

            # Force the next_run to past
            scheduler._tasks[0]["next_run"] = datetime.now() - timedelta(minutes=10)
            original_next = scheduler._tasks[0]["next_run"]

            due = scheduler.get_due_tasks()
            assert len(due) == 1
            # Should have rescheduled
            assert scheduler._tasks[0]["next_run"] > original_next
        finally:
            Path(store_path).unlink(missing_ok=True)

    def test_one_shot_removed_after_firing(self):
        store_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            scheduler = Scheduler(store_path=store_path)
            task = Task(task_id="t_os", task_type="write", params={})
            scheduler.add_one_shot_task(task, datetime.now())

            due = scheduler.get_due_tasks()
            assert len(due) == 1
            # Task should be gone from store after firing
            store = TaskStore(store_path)
            assert store.get_task_count() == 0
        finally:
            Path(store_path).unlink(missing_ok=True)

    def test_task_store_update_next_run(self):
        """update_next_run should persist."""
        store_path = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            from orchestrator.task_store import TaskStore

            store = TaskStore(store_path)
            store.save_task("s1", "write", "t1", {})
            new_time = datetime(2026, 8, 1, 12, 0)
            store.update_next_run("s1", new_time)
            tasks = store.load_tasks()
            assert tasks[0]["next_run"] == "2026-08-01T12:00:00"
        finally:
            Path(store_path).unlink(missing_ok=True)

    def test_get_status(self):
        scheduler = Scheduler()
        scheduler.add_recurring_task(
            Task(task_id="t1", task_type="write", params={}),
            interval_minutes=60,
        )
        status = scheduler.get_status()
        assert status["running"] is False
        assert status["scheduled_tasks"] == 1
        assert "store_path" in status
