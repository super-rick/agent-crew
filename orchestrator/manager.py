"""
Orchestrator — task dispatch and agent coordination.

Orchestrator 是系统中的"导演"：
- 协调多个 Agent 完成复杂任务
- 管理任务队列和生命周期
- 记录任务历史和调度周期
- 是唯一知道所有 Agent 的组件

核心流程：
    execute_pipeline(task) ->
        if write_and_publish:
            writer_agent.execute(write_task)
            publisher_agent.execute(publish_task)
        return aggregated_result
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from agents.base import BaseAgent, Task, TaskResult


@dataclass
class PipelineResult:
    """Combined result from a multi-agent pipeline execution."""

    success: bool
    pipeline_id: str
    task_type: str
    results: dict[str, TaskResult] = field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "pipeline_id": self.pipeline_id,
            "task_type": self.task_type,
            "results": {name: r.to_dict() for name, r in self.results.items()},
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


class Orchestrator:
    """Central coordinator that manages Agent interaction."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.agents: dict[str, BaseAgent] = {}
        self.task_history: list[PipelineResult] = []
        self._scheduler = None

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent by its name."""
        self.agents[agent.name] = agent

    def get_agent(self, name: str) -> BaseAgent:
        """Get a registered agent by name."""
        if name not in self.agents:
            raise KeyError(
                f"Agent '{name}' not registered. " f"Available: {list(self.agents.keys())}"
            )
        return self.agents[name]

    def create_task(
        self,
        task_type: str,
        params: dict | None = None,
        scheduled_at: datetime | None = None,
    ) -> Task:
        """Create a new task with a unique ID."""
        return Task(
            task_id=str(uuid4())[:8],
            task_type=task_type,
            params=params or {},
            scheduled_at=scheduled_at,
        )

    def execute_pipeline(self, task: Task) -> PipelineResult:
        """Execute a task pipeline that may involve multiple agents.

        Supported task_types:
            - "write": WriterAgent only
            - "publish": PublisherAgent only
            - "write_and_publish": Writer + Publisher in sequence
            - "analyst": AnalystAgent only
            - "schedule": Scheduler only
        """
        started_at = datetime.now()
        pipeline_id = str(uuid4())[:8]
        results: dict[str, TaskResult] = {}
        agents_required = self._agents_for_task(task.task_type)

        # Verify required agents are registered
        for agent_name in agents_required:
            if agent_name not in self.agents:
                return PipelineResult(
                    success=False,
                    pipeline_id=pipeline_id,
                    task_type=task.task_type,
                    error_message=f"Required agent '{agent_name}' not registered",
                    started_at=started_at,
                )

        try:
            if task.task_type == "write":
                agent = self.agents["writer"]
                result = agent.execute(task)
                results["writer"] = result

            elif task.task_type == "publish":
                agent = self.agents["publisher"]
                result = agent.execute(task)
                results["publisher"] = result

            elif task.task_type == "write_and_publish":
                # Step 1: Writer generates content
                writer = self.agents["writer"]
                write_task = Task(
                    task_id=f"{task.task_id}_write",
                    task_type="write",
                    params=task.params,
                )
                write_result = writer.execute(write_task)
                results["writer"] = write_result

                # Step 2: Publisher distributes the generated content
                if write_result.success:
                    publisher = self.agents["publisher"]
                    content_data = write_result.data
                    publish_task = Task(
                        task_id=f"{task.task_id}_pub",
                        task_type="publish",
                        params={
                            "content": {
                                "text": content_data.get(
                                    "formatted_content", content_data.get("raw_content", "")
                                ),
                                "title": f"关于 {task.params.get('topic', '')} 的分享",
                            },
                            "platforms": task.params.get(
                                "platforms", publisher.config.get("default_platforms", [])
                            ),
                            "dry_run": task.params.get("dry_run", False),
                        },
                    )
                    pub_result = publisher.execute(publish_task)
                    results["publisher"] = pub_result
                else:
                    # Writer failed, skip publishing
                    results["publisher"] = TaskResult(
                        task_id=f"{task.task_id}_pub",
                        success=False,
                        error_message="Skipped: writer agent failed",
                        agent_name="publisher",
                    )

            elif task.task_type == "schedule":
                # Schedule is handled by Scheduler, just ack
                pass

            elif task.task_type == "analyst":
                agent = self.agents["analyst"]
                result = agent.execute(task)
                results["analyst"] = result

            else:
                raise ValueError(f"Unknown task_type: {task.task_type}")

            all_success = all(r.success for r in results.values())
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            pipeline_result = PipelineResult(
                success=all_success,
                pipeline_id=pipeline_id,
                task_type=task.task_type,
                results=results,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

            self.task_history.append(pipeline_result)
            return pipeline_result

        except Exception as e:
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()
            pipeline_result = PipelineResult(
                success=False,
                pipeline_id=pipeline_id,
                task_type=task.task_type,
                results=results,
                error_message=str(e),
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )
            self.task_history.append(pipeline_result)
            return pipeline_result

    def run_cycle(self) -> list[PipelineResult]:
        """Run one scheduling cycle — execute all due tasks.

        Called by the Scheduler at each tick.
        """
        if not self._scheduler:
            return []

        due_tasks = self._scheduler.get_due_tasks()
        results = []
        for task in due_tasks:
            result = self.execute_pipeline(task)
            results.append(result)

        return results

    def set_scheduler(self, scheduler) -> None:
        """Set the scheduler instance for this orchestrator."""
        self._scheduler = scheduler

    def get_history(self, limit: int = 20) -> list[PipelineResult]:
        """Return the most recent pipeline results."""
        return self.task_history[-limit:]

    def _agents_for_task(self, task_type: str) -> list[str]:
        """Determine which agents are needed for a task type."""
        mapping = {
            "write": ["writer"],
            "publish": ["publisher"],
            "write_and_publish": ["writer", "publisher"],
            "analyst": ["analyst"],
            "schedule": [],
        }
        return mapping.get(task_type, [])

    def __repr__(self) -> str:
        agents = ", ".join(self.agents.keys())
        return f"Orchestrator(agents=[{agents}], history={len(self.task_history)})"
