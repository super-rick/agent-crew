"""
Skill system — orchestrated workflows composed of Tools.

Skill = 多个 Tool 的有序编排，赋予 Agent 复杂能力。
比如 "追热点写作 Skill" 内部是：
    get_current_time → web_search(trending topics) → RAG.retrieve → LLM.generate

v0.1 的 Skill.workflow 是 Python 函数（确定式编排），
v2 计划升级为 "LLM 根据 Skill 描述自主选择 Tool 调用顺序"（动态编排）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from agents.tools import ToolRegistry


@dataclass
class SkillResult:
    """Result of executing a Skill."""

    success: bool
    skill_name: str
    data: Any = None
    error_message: str | None = None
    tool_calls: list[dict] = field(default_factory=list)


class Skill(ABC):
    """A composable capability built from multiple Tools.

    A Skill defines:
    - name: identifier
    - description: what this skill does
    - required_tools: which Tools must be registered
    - execute(): the orchestration logic
    """

    name: str
    description: str
    required_tools: list[str]

    @abstractmethod
    def execute(self, registry: ToolRegistry, params: dict) -> SkillResult:
        """Execute the skill using tools from the registry."""


class SkillRegistry:
    """Registry that manages an Agent's Skills."""

    def __init__(self):
        self._skills: dict[str, type[Skill]] = {}
        self._skill_instances: dict[str, Skill] = {}

    def register(self, skill_class: type[Skill]) -> None:
        """Register a Skill class. The class will be instantiated on first use."""
        name = skill_class.name
        self._skills[name] = skill_class

    def register_instance(self, skill: Skill) -> None:
        """Register an already-instantiated Skill."""
        self._skill_instances[skill.name] = skill

    def get(self, name: str) -> Skill:
        """Get a skill by name (instantiated)."""
        if name in self._skill_instances:
            return self._skill_instances[name]
        if name in self._skills:
            instance = self._skills[name]()
            self._skill_instances[name] = instance
            return instance
        raise KeyError(f"Skill '{name}' not found. Available: {self.list_names()}")

    def list_skills(self) -> list[Skill]:
        """Return all registered skills (instantiated)."""
        return [self.get(name) for name in self._skill_instances | self._skills]

    def list_names(self) -> list[str]:
        """Return names of all registered skills."""
        return list(set(self._skills.keys()) | set(self._skill_instances.keys()))

    def execute(self, name: str, registry: ToolRegistry, params: dict) -> SkillResult:
        """Execute a skill by name."""
        skill = self.get(name)
        # Verify all required tools are available
        for tool_name in skill.required_tools:
            if tool_name not in registry:
                return SkillResult(
                    success=False,
                    skill_name=name,
                    error_message=f"Required tool '{tool_name}' not in registry",
                )
        return skill.execute(registry, params)


# ============================================================
# Built-in Skills
# ============================================================


class TrendingWritingSkill(Skill):
    """追热点写作 — 搜索热点 + LLM 生成热榜内容"""

    name = "trending_writing"
    description = "搜索当下热点话题，基于热点生成有吸引力的内容"
    required_tools = ["web_search", "get_current_time"]

    def execute(self, registry: ToolRegistry, params: dict) -> SkillResult:
        topic = params.get("topic", params.get("title", ""))
        style = params.get("style", "technical")
        platform = params.get("platform", "generic")

        # Step 1: Get current time for context
        now = registry.execute("get_current_time")

        # Step 2: Search for trending content about the topic
        search_results = registry.execute(
            "web_search", query=f"{topic} 2026 趋势 技术", max_results=5
        )

        # Step 3: Build context from search results
        context_parts = []
        for r in search_results:
            context_parts.append(f"- {r['title']}: {r['snippet']}")

        context = "\n".join(context_parts)

        return SkillResult(
            success=True,
            skill_name=self.name,
            data={
                "topic": topic,
                "style": style,
                "platform": platform,
                "current_time": now,
                "search_context": context,
                "search_results": search_results,
            },
            tool_calls=[
                {"tool": "get_current_time", "result": now},
                {"tool": "web_search", "args": {"query": f"{topic} 2026 趋势 技术"}},
            ],
        )


class TechnicalArticleSkill(Skill):
    """技术文章写作 — 结合搜索和深度思考生成技术长文"""

    name = "technical_article"
    description = "生成深度技术文章，适合掘金等开发者社区"
    required_tools = ["web_search"]

    def execute(self, registry: ToolRegistry, params: dict) -> SkillResult:
        topic = params.get("topic", "")
        platform = params.get("platform", "juejin")

        # Search for reference material
        search_results = registry.execute(
            "web_search", query=f"{topic} 技术教程 实践", max_results=3
        )

        context = "\n".join(f"- {r['title']}: {r['snippet']}" for r in search_results)

        return SkillResult(
            success=True,
            skill_name=self.name,
            data={
                "topic": topic,
                "platform": platform,
                "search_context": context,
                "search_results": search_results,
            },
            tool_calls=[
                {"tool": "web_search", "args": {"query": f"{topic} 技术教程 实践"}},
            ],
        )


class ThreadWritingSkill(Skill):
    """Thread 写作 — 生成适合社交媒体的 Thread 内容"""

    name = "thread_writing"
    description = "生成 Thread/帖子形式的内容，适合 X/Twitter 等社交平台"
    required_tools = ["get_current_time"]

    def execute(self, registry: ToolRegistry, params: dict) -> SkillResult:
        topic = params.get("topic", "")
        platform = params.get("platform", "twitter")

        now = registry.execute("get_current_time")

        return SkillResult(
            success=True,
            skill_name=self.name,
            data={
                "topic": topic,
                "platform": platform,
                "current_time": now,
            },
            tool_calls=[
                {"tool": "get_current_time", "result": now},
            ],
        )


# All built-in skills for automatic registration
BUILTIN_SKILLS: list[type[Skill]] = [
    TrendingWritingSkill,
    TechnicalArticleSkill,
    ThreadWritingSkill,
]
