"""
Scheduler — timing engine with anti-detection jitter + persistence.

定时调度引擎，带随机抖动以防止平台检测 + JSON 文件持久化。

核心特性:
1. 随机抖动: interval + random(-jitter, +jitter) 反检测
2. JSON 持久化: 进程重启后可恢复未完成任务
3. Cron 表达式: 支持标准 5 字段 cron 格式
4. schedule resume: 从 JSON 文件恢复并继续执行
"""

from __future__ import annotations

import random
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable

from agents.base import Task

# ── Cron parser ──────────────────────────────────────────────────────

_CRON_FIELD_RANGES = [
    (0, 59),  # minute
    (0, 23),  # hour
    (1, 31),  # day of month
    (1, 12),  # month
    (0, 6),  # day of week (0=Sun)
]

_FIELD_NAMES = ["minute", "hour", "day", "month", "weekday"]


def _parse_cron_field(field: str, min_val: int, max_val: int) -> set[int]:
    """Parse a single cron field into a set of allowed values."""
    if field == "*":
        return set(range(min_val, max_val + 1))

    values: set[int] = set()
    parts = field.split(",")

    for part in parts:
        if "/" in part:
            base, step = part.split("/")
            s = int(step)
            if base == "*":
                base_range = range(min_val, max_val + 1)
            else:
                b = int(base)
                base_range = range(b, max_val + 1)
            values.update(base_range[::s])
        elif "-" in part:
            lo, hi = part.split("-")
            values.update(range(int(lo), int(hi) + 1))
        else:
            v = int(part)
            if min_val <= v <= max_val:
                values.add(v)

    return values


def next_cron_time(expression: str, after: datetime | None = None) -> datetime:
    """Calculate the next datetime matching a cron expression.

    Supports standard 5-field format: "minute hour day month weekday"
    Examples:
        "0 9 * * 1-5"  → 9:00 AM weekdays
        "0 */6 * * *"  → every 6 hours
        "30 14 * * *"  → 2:30 PM daily

    Args:
        expression: 5-field cron string.
        after: Reference time (default: now).

    Returns:
        The next datetime matching the expression.
    """
    fields = expression.strip().split()
    if len(fields) != 5:
        raise ValueError(f"Cron expression must have 5 fields, got {len(fields)}: {expression}")

    parsed = []
    for i, field in enumerate(fields):
        min_v, max_v = _CRON_FIELD_RANGES[i]
        vals = _parse_cron_field(field, min_v, max_v)
        if not vals:
            raise ValueError(f"Empty cron field '{field}' at position {i}")
        parsed.append(sorted(vals))

    now = after or datetime.now()
    current = now.replace(second=0, microsecond=0) + timedelta(minutes=1)

    # Try up to 2 years ahead to find a match
    max_iterations = 2 * 366 * 24 * 60
    for _ in range(max_iterations):
        if (
            current.minute in parsed[0]
            and current.hour in parsed[1]
            and current.day in parsed[2]
            and current.month in parsed[3]
            and current.weekday() in parsed[4]
        ):
            return current
        current += timedelta(minutes=1)

    # Fallback: return now + 1 hour
    return now + timedelta(hours=1)


def is_valid_cron(expression: str) -> bool:
    """Check if a string is a valid 5-field cron expression."""
    try:
        fields = expression.strip().split()
        if len(fields) != 5:
            return False
        for i, field in enumerate(fields):
            min_v, max_v = _CRON_FIELD_RANGES[i]
            vals = _parse_cron_field(field, min_v, max_v)
            if not vals:
                return False
        return True
    except (ValueError, IndexError):
        return False


# ── Scheduler ────────────────────────────────────────────────────────


class Scheduler:
    """Timing scheduler with random jitter + JSON persistence + cron support.

    Persists tasks to a JSON file so running tasks survive restarts.
    Supports interval-based and cron-based scheduling.
    """

    def __init__(
        self,
        min_interval_min: int = 120,
        jitter_min: int = 30,
        store_path: str = "data/scheduler.json",
    ):
        self.min_interval_min = min_interval_min
        self.jitter_min = jitter_min
        self._tasks: list[dict] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._execute_callback: Callable[[Task], Any] | None = None

        # Persistence
        from orchestrator.task_store import TaskStore

        self._store = TaskStore(store_path)

    @property
    def store_path(self) -> str:
        return str(self._store.file_path)

    def set_callback(self, callback: Callable[[Task], Any]) -> None:
        """Set the callback to execute when a task fires."""
        self._execute_callback = callback

    def add_recurring_task(
        self,
        task_template: Task,
        interval_minutes: float = 0,
        cron: str | None = None,
    ) -> str:
        """Add a recurring task with interval or cron expression.

        Args:
            task_template: The task to execute.
            interval_minutes: Interval in minutes (used if cron is None).
            cron: 5-field cron expression, e.g. "0 9 * * 1-5".

        Returns:
            schedule_id string.
        """
        now = datetime.now()

        if cron and is_valid_cron(cron):
            next_run = next_cron_time(cron, after=now)
        elif interval_minutes > 0:
            next_run = now + timedelta(minutes=self._apply_jitter(interval_minutes))
        else:
            next_run = now + timedelta(minutes=60)  # Default: 1 hour

        schedule_id = f"{task_template.task_id}_rec"

        entry = {
            "task": task_template,
            "interval_minutes": interval_minutes,
            "cron": cron,
            "next_run": next_run,
            "schedule_id": schedule_id,
        }
        self._tasks.append(entry)

        # Persist to JSON store
        self._store.save_task(
            schedule_id=schedule_id,
            task_type=task_template.task_type,
            task_id=task_template.task_id,
            params=task_template.params,
            interval_minutes=interval_minutes,
            cron_expression=cron,
            next_run=next_run,
        )

        return schedule_id

    def add_one_shot_task(self, task: Task, execute_at: datetime) -> str:
        """Add a one-shot task to execute at a specific time."""
        entry = {
            "task": task,
            "interval_minutes": 0,
            "next_run": execute_at,
            "schedule_id": f"{task.task_id}_oneshot",
            "one_shot": True,
        }
        self._tasks.append(entry)

        self._store.save_task(
            schedule_id=entry["schedule_id"],
            task_type=task.task_type,
            task_id=task.task_id,
            params=task.params,
            next_run=execute_at,
            is_one_shot=True,
        )

        return task.task_id

    def load_from_store(self) -> int:
        """Restore scheduled tasks from the JSON store.

        Called by `schedule resume` to restore state after a restart.
        Returns the number of tasks restored.
        """
        stored = self._store.load_tasks()
        count = 0
        for item in stored:
            task = Task(
                task_id=item["task_id"],
                task_type=item["task_type"],
                params=item.get("params", {}),
            )
            next_run = datetime.fromisoformat(item["next_run"])
            # If next_run is in the past, reschedule now
            if next_run < datetime.now() and not item.get("is_one_shot"):
                next_run = datetime.now() + timedelta(minutes=1)

            entry = {
                "task": task,
                "interval_minutes": item.get("interval_minutes", 0),
                "cron": item.get("cron_expression"),
                "next_run": next_run,
                "schedule_id": item["schedule_id"],
                "one_shot": item.get("is_one_shot", False),
            }
            self._tasks.append(entry)
            count += 1

        return count

    def get_due_tasks(self) -> list[Task]:
        """Return all tasks whose next_run time has passed, and schedule next runs."""
        now = datetime.now()
        due: list[Task] = []
        remaining: list[dict] = []

        for entry in self._tasks:
            if entry["next_run"] <= now:
                due.append(entry["task"])

                if entry.get("one_shot"):
                    self._store.remove_task(entry["schedule_id"])
                    continue

                # Reschedule
                if entry.get("cron") and is_valid_cron(entry["cron"]):
                    entry["next_run"] = next_cron_time(entry["cron"], after=now)
                else:
                    interval = entry.get("interval_minutes", 60)
                    entry["next_run"] = now + timedelta(minutes=self._apply_jitter(interval))

                # Persist updated next_run
                self._store.update_next_run(entry["schedule_id"], entry["next_run"])

            remaining.append(entry)

        self._tasks = remaining
        return due

    def _apply_jitter(self, interval_minutes: float) -> float:
        """Add random jitter for anti-detection."""
        jitter = random.uniform(-self.jitter_min, self.jitter_min)
        return max(self.min_interval_min, interval_minutes + jitter)

    def start(self, block: bool = False) -> None:
        """Start the scheduler loop."""
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
        """Main loop — polls every 30 seconds for due tasks."""
        while self._running:
            try:
                if self._execute_callback:
                    due = self.get_due_tasks()
                    for task in due:
                        self._execute_callback(task)
            except Exception:
                pass
            for _ in range(30):
                if not self._running:
                    break
                time.sleep(1)

    def get_next_run_times(self, n: int = 10) -> list[tuple[str, datetime]]:
        """Return the next N scheduled run times."""
        sorted_tasks = sorted(self._tasks, key=lambda t: t["next_run"])
        return [(t["schedule_id"], t["next_run"]) for t in sorted_tasks[:n]]

    def cancel(self, schedule_id: str) -> bool:
        """Cancel a scheduled task."""
        for i, entry in enumerate(self._tasks):
            if entry["schedule_id"] == schedule_id:
                self._tasks.pop(i)
                self._store.remove_task(schedule_id)
                return True
        return False

    def is_running(self) -> bool:
        return self._running

    def set_smart_schedule(
        self,
        best_hours: list[int],
        tasks: list,
        days: int = 1,
    ) -> None:
        """Distribute tasks across recommended hours over N days.

        Used with AnalystAgent.predict_best_times() for optimal scheduling.
        Tasks are spread evenly across the best time slots.
        """
        if not tasks or not best_hours:
            return

        now = datetime.now()
        slots_per_day = len(best_hours)
        per_slot = max(1, len(tasks) // (slots_per_day * days))

        task_idx = 0
        for day_offset in range(days):
            for hour in best_hours:
                slot_time = (now + timedelta(days=day_offset)).replace(
                    hour=hour, minute=0, second=0, microsecond=0
                )
                if slot_time <= now:
                    slot_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

                for _ in range(per_slot):
                    if task_idx >= len(tasks):
                        return
                    task = tasks[task_idx]
                    task_idx += 1
                    self.add_one_shot_task(task, slot_time)
                    slot_time += timedelta(minutes=5)  # Spread within slot

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "scheduled_tasks": len(self._tasks),
            "min_interval_min": self.min_interval_min,
            "jitter_min": self.jitter_min,
            "next_runs": self.get_next_run_times(5),
            "store_path": self.store_path,
        }
