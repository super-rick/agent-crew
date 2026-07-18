"""
Scheduler — timing engine with anti-detection jitter.

定时调度引擎，带随机抖动以防止平台检测。
使用 schedule 库 + 后台线程。

核心策略：
1. 每次调度间隔加随机抖动：interval + random(-jitter, +jitter)
2. 最小间隔保护：防止过于频繁的发布
3. 可查看接下来的调度时间（预览用）
"""

from __future__ import annotations

import random
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable

from agents.base import Task


class Scheduler:
    """Timing scheduler with random jitter for anti-detection.

    v0.1: 前台进程 + 后台线程（Ctrl+C 停止）
    v2: 可升级为后台 daemon 或 external cron
    """

    def __init__(
        self,
        min_interval_min: int = 120,
        jitter_min: int = 30,
    ):
        self.min_interval_min = min_interval_min
        self.jitter_min = jitter_min
        self._tasks: list[dict] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._execute_callback: Callable[[Task], Any] | None = None

    def set_callback(self, callback: Callable[[Task], Any]) -> None:
        """Set the callback to execute when a task fires.

        Typically wired to Orchestrator.execute_pipeline().
        """
        self._execute_callback = callback

    def add_recurring_task(
        self,
        task_template: Task,
        interval_minutes: float,
    ) -> str:
        """Add a recurring task.

        The task will fire at jittered intervals.
        Returns a task_id for cancellation.
        """
        schedule_entry = {
            "task": task_template,
            "interval_minutes": interval_minutes,
            "next_run": datetime.now() + timedelta(minutes=self._apply_jitter(interval_minutes)),
            "schedule_id": task_template.task_id,
        }
        self._tasks.append(schedule_entry)
        return task_template.task_id

    def add_one_shot_task(self, task: Task, execute_at: datetime) -> str:
        """Add a one-shot task to execute at a specific time."""
        schedule_entry = {
            "task": task,
            "interval_minutes": 0,
            "next_run": execute_at,
            "schedule_id": f"{task.task_id}_oneshot",
            "one_shot": True,
        }
        self._tasks.append(schedule_entry)
        return task.task_id

    def get_due_tasks(self) -> list[Task]:
        """Return all tasks whose next_run time has passed, and schedule next runs.

        Called by Orchestrator.run_cycle().
        """
        now = datetime.now()
        due: list[Task] = []
        remaining: list[dict] = []

        for entry in self._tasks:
            if entry["next_run"] <= now:
                due.append(entry["task"])

                if entry.get("one_shot"):
                    # One-shot tasks are removed after firing
                    continue

                # Reschedule with jitter
                entry["next_run"] = now + timedelta(
                    minutes=self._apply_jitter(entry["interval_minutes"])
                )
            remaining.append(entry)

        self._tasks = remaining
        return due

    def _apply_jitter(self, interval_minutes: float) -> float:
        """Add random jitter: interval + random(-jitter, +jitter).

        This is the core anti-detection mechanism.
        Randomization prevents platforms from detecting fixed-interval posting.
        """
        jitter = random.uniform(-self.jitter_min, self.jitter_min)
        return max(self.min_interval_min, interval_minutes + jitter)

    def start(self, block: bool = False) -> None:
        """Start the scheduler loop.

        Args:
            block: If True, runs in the current thread (blocking).
                   If False, runs in a background thread.
        """
        if self._running:
            return

        self._running = True

        if block:
            self._loop()
        else:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False

    def _loop(self) -> None:
        """Main scheduler loop — polls every 30 seconds for due tasks."""
        while self._running:
            try:
                if self._execute_callback:
                    due = self.get_due_tasks()
                    for task in due:
                        self._execute_callback(task)
            except Exception:
                # Silently continue — prevent scheduler from crashing
                pass

            for _ in range(30):
                if not self._running:
                    break
                time.sleep(1)

    def get_next_run_times(self, n: int = 10) -> list[tuple[str, datetime]]:
        """Return the next N scheduled run times.

        Useful for CLI display.
        """
        sorted_tasks = sorted(self._tasks, key=lambda t: t["next_run"])
        return [(t["task"].task_id, t["next_run"]) for t in sorted_tasks[:n]]

    def cancel(self, schedule_id: str) -> bool:
        """Cancel a scheduled task by its schedule_id."""
        for i, entry in enumerate(self._tasks):
            if entry["schedule_id"] == schedule_id:
                self._tasks.pop(i)
                return True
        return False

    def is_running(self) -> bool:
        """Return whether the scheduler loop is active."""
        return self._running

    def get_status(self) -> dict:
        """Return scheduler status overview."""
        return {
            "running": self._running,
            "scheduled_tasks": len(self._tasks),
            "min_interval_min": self.min_interval_min,
            "jitter_min": self.jitter_min,
            "next_runs": self.get_next_run_times(5),
        }
