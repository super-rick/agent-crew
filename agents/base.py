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

    def _build_messages(self, user_content: str) -> list[dict]:
        """Build the standard messages list for LLM calls."""
        return [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": user_content},
        ]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
