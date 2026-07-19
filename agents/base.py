"""
Base Agent abstract class — all AI employees inherit from this.

每个 Agent 是一个独立的 AI 员工，拥有：
- 自己的 system prompt（角色定义）
- 注册的 Tools（原子操作）
- 注册的 Skills（Tool 的编排组合）
- 通过 Orchestrator 协调与其他 Agent 的协作
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from llm.client import LLMClient


@dataclass
class Task:
    """A unit of work dispatched to an Agent."""

    task_id: str
    task_type: str  # "write", "publish", "write_and_publish"
    params: dict = field(default_factory=dict)
    status: str = "pending"  # pending | running | completed | failed
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any = None


@dataclass
class TaskResult:
    """Result returned after an Agent completes a Task."""

    task_id: str
    success: bool
    data: Any = None
    error_message: str | None = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    agent_name: str = ""
    retry_count: int = 0

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "agent_name": self.agent_name,
            "retry_count": self.retry_count,
        }


class BaseAgent(ABC):
    """Abstract base for all AI employee Agents.

    Subclasses must implement:
        name: str — unique identifier
        description: str — what this agent does
        get_system_prompt() -> str — the system prompt defining the agent's role
        execute(task: Task) -> TaskResult — core execution logic
    """

    name: str = "base"
    description: str = "Base agent"

    def __init__(
        self,
        llm_client: LLMClient,
        config: dict | None = None,
        tool_registry=None,
        skill_registry=None,
    ):
        self.llm_client = llm_client
        self.config = config or {}
        self._tool_registry = tool_registry
        self._skill_registry = skill_registry

    @property
    def tool_registry(self):
        if self._tool_registry is None:
            raise RuntimeError(f"ToolRegistry not injected into {self.name}")
        return self._tool_registry

    @tool_registry.setter
    def tool_registry(self, registry):
        self._tool_registry = registry

    @property
    def skill_registry(self):
        if self._skill_registry is None:
            raise RuntimeError(f"SkillRegistry not injected into {self.name}")
        return self._skill_registry

    @skill_registry.setter
    def skill_registry(self, registry):
        self._skill_registry = registry

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt defining this agent's role and behavior."""

    @abstractmethod
    def execute(self, task: Task) -> TaskResult:
        """Execute a task and return the result."""

    def execute_with_retry(
        self,
        task: Task,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_factor: float = 2.0,
    ) -> TaskResult:
        """Execute a task with exponential backoff retry.

        On failure, retries up to max_retries times with increasing delays:
            delay = backoff_base * (backoff_factor ** attempt) + jitter

        Args:
            task: The task to execute.
            max_retries: Max retry attempts after initial failure (default 3).
            backoff_base: Base delay in seconds (default 1.0).
            backoff_factor: Exponential multiplier (default 2.0).

        Returns:
            TaskResult with retry_count set to the attempt number.
        """
        import random
        import time
        from datetime import datetime

        started_at = datetime.now()
        last_result = None

        for attempt in range(max_retries + 1):
            try:
                result = self.execute(task)
                result.retry_count = attempt

                if result.success:
                    result.started_at = started_at
                    result.completed_at = datetime.now()
                    result.duration_seconds = (result.completed_at - started_at).total_seconds()
                    return result

                last_result = result

                if attempt < max_retries:
                    delay = backoff_base * (backoff_factor**attempt)
                    delay = min(delay, 60.0)
                    delay *= 1.0 + random.uniform(-0.25, 0.25)
                    time.sleep(max(0, delay))

            except Exception as e:
                if attempt >= max_retries:
                    return TaskResult(
                        task_id=task.task_id,
                        success=False,
                        error_message=f"All {max_retries + 1} attempts failed: {e}",
                        started_at=started_at,
                        completed_at=datetime.now(),
                        agent_name=self.name,
                        retry_count=attempt,
                    )
                delay = backoff_base * (backoff_factor**attempt)
                delay = min(delay, 60.0)
                delay *= 1.0 + random.uniform(-0.25, 0.25)
                time.sleep(max(0, delay))

        completed_at = datetime.now()
        if last_result:
            last_result.started_at = started_at
            last_result.completed_at = completed_at
            last_result.duration_seconds = (completed_at - started_at).total_seconds()
            return last_result

        return TaskResult(
            task_id=task.task_id,
            success=False,
            error_message=f"Exhausted {max_retries + 1} attempts",
            started_at=started_at,
            completed_at=completed_at,
            agent_name=self.name,
            retry_count=max_retries,
        )

    def _build_messages(self, user_content: str) -> list[dict]:
        """Build the standard messages list for LLM calls."""
        return [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": user_content},
        ]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
