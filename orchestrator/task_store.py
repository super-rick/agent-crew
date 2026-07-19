"""
Persistent task store backed by JSON file.

Stores scheduled tasks so they survive process restarts.
Used by Scheduler for persistence and `schedule resume`.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_STORE_PATH = "data/scheduler.json"


class TaskStore:
    """JSON file-backed persistent store for scheduled tasks.

    Lightweight alternative to SQLite. Suitable for task counts < 1000.
    Uses a file lock to prevent concurrent write corruption.
    """

    def __init__(self, file_path: str = DEFAULT_STORE_PATH):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.file_path.exists():
            self._write([])

    def _read(self) -> list[dict[str, Any]]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write(self, tasks: list[dict[str, Any]]) -> None:
        # Atomic write: write to temp file, then rename
        tmp = self.file_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
        tmp.rename(self.file_path)

    def save_task(
        self,
        schedule_id: str,
        task_type: str,
        task_id: str,
        params: dict,
        interval_minutes: float = 0,
        cron_expression: str | None = None,
        next_run: datetime | None = None,
        is_one_shot: bool = False,
        extra: dict | None = None,
    ) -> None:
        """Persist a scheduled task (upsert by schedule_id)."""
        with self._lock:
            tasks = self._read()
            entry = {
                "schedule_id": schedule_id,
                "task_type": task_type,
                "task_id": task_id,
                "params": params,
                "interval_minutes": interval_minutes,
                "cron_expression": cron_expression,
                "next_run": (next_run or datetime.now()).isoformat(),
                "is_one_shot": is_one_shot,
                "extra": extra or {},
            }
            # Upsert: replace if exists
            for i, t in enumerate(tasks):
                if t.get("schedule_id") == schedule_id:
                    tasks[i] = entry
                    break
            else:
                tasks.append(entry)
            self._write(tasks)

    def update_next_run(self, schedule_id: str, next_run: datetime) -> None:
        """Update the next_run time for a scheduled task."""
        with self._lock:
            tasks = self._read()
            for t in tasks:
                if t.get("schedule_id") == schedule_id:
                    t["next_run"] = next_run.isoformat()
                    break
            self._write(tasks)

    def remove_task(self, schedule_id: str) -> bool:
        """Remove a task. Returns True if deleted."""
        with self._lock:
            tasks = self._read()
            before = len(tasks)
            tasks = [t for t in tasks if t.get("schedule_id") != schedule_id]
            if len(tasks) < before:
                self._write(tasks)
                return True
            return False

    def load_tasks(self) -> list[dict[str, Any]]:
        """Load all scheduled tasks."""
        return self._read()

    def get_task_count(self) -> int:
        return len(self._read())

    def clear_all(self) -> int:
        """Remove all tasks. Returns count of deleted rows."""
        with self._lock:
            tasks = self._read()
            count = len(tasks)
            self._write([])
            return count

    def close(self) -> None:
        pass  # No connection to close
