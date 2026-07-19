"""
Skill system — orchestrated workflows composed of Tools.

Skill = 多个 Tool 的有序编排，赋予 Agent 复杂能力。
比如 "追热点写作 Skill" 内部是：
    get_current_time → web_search(trending topics) → RAG.retrieve → LLM.generate

v0.3: deterministic workflow — Python function defines tool call order.
v0.4: LLM-driven mode — LLM chooses tool order based on description + context.
      Backward compatible via workflow_type: "deterministic" | "llm_driven".
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
    workflow_type: str = "deterministic"  # "deterministic" | "llm_driven"

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

    def execute(
        self,
        name: str,
        registry: ToolRegistry,
        params: dict,
        llm_client=None,
    ) -> SkillResult:
        """Execute a skill by name.

        For deterministic skills, calls the skill's execute().
        For LLM-driven skills, uses the LLM to plan and execute tool calls.

        Args:
            name: Skill name to execute.
            registry: ToolRegistry with available tools.
            params: Task parameters (topic, style, platform, etc.).
            llm_client: Required for LLM-driven skills.
        """
        skill = self.get(name)

        if skill.workflow_type == "llm_driven":
            if llm_client is None:
                return SkillResult(
                    success=False,
                    skill_name=name,
                    error_message="LLM client required for llm_driven skill",
                )
            return self._execute_llm_driven(skill, registry, params, llm_client)

        # Verify required tools for deterministic skills
        for tool_name in skill.required_tools:
            if tool_name not in registry:
                return SkillResult(
                    success=False,
                    skill_name=name,
                    error_message=f"Required tool '{tool_name}' not in registry",
                )

        return skill.execute(registry, params)

    def _execute_llm_driven(
        self,
        skill: Skill,
        registry: ToolRegistry,
        params: dict,
        llm_client,
    ) -> SkillResult:
        """Let the LLM decide which tools to call and in what order."""
        tools_desc = registry.describe_all()

        topic = params.get("topic", params.get("title", ""))
        style = params.get("style", "technical")
        platform = params.get("platform", "generic")

        # Build the planning prompt
        prompt = (
            f"You are executing the '{skill.name}' skill: {skill.description}\n\n"
            f"Task parameters:\n"
            f"  topic: {topic}\n"
            f"  style: {style}\n"
            f"  platform: {platform}\n\n"
            f"Available tools:\n{tools_desc}\n\n"
            "Plan: call the appropriate tools in the right order. "
            "Use the get_current_time tool first if the skill needs time context. "
            "Use web_search to gather information about the topic. "
            "Return your plan as a JSON array of tool calls:\n"
            '[{"tool": "tool_name", "args": {"arg1": "value1"}}, ...]\n'
        )

        messages = [
            {"role": "system", "content": "You are a workflow planner. Plan tool calls as JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = llm_client.chat(messages)

            # Parse LLM's tool call plan
            import json as _json

            try:
                plan = _json.loads(response)
                if not isinstance(plan, list):
                    plan = []
            except _json.JSONDecodeError:
                # Try to extract JSON from the response
                import re as _re

                match = _re.search(r"\[.*\]", response, _re.DOTALL)
                if match:
                    try:
                        plan = _json.loads(match.group())
                    except _json.JSONDecodeError:
                        plan = []
                else:
                    plan = []

            # Execute the planned tool calls
            tool_calls = []
            context_parts = []

            for step in plan:
                tool_name = step.get("tool", "")
                tool_args = step.get("args", {})

                if tool_name not in registry:
                    continue

                try:
                    result = registry.execute(tool_name, **tool_args)
                    tool_calls.append(
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "result": str(result)[:500],
                        }
                    )

                    if tool_name == "web_search" and isinstance(result, list):
                        for r in result:
                            context_parts.append(f"- {r.get('title', '')}: {r.get('snippet', '')}")
                    elif tool_name == "get_current_time":
                        context_parts.append(f"Current time: {result}")
                    elif isinstance(result, str):
                        context_parts.append(result)
                except Exception as e:
                    tool_calls.append({"tool": tool_name, "args": tool_args, "error": str(e)})

            search_context = "\n".join(context_parts) if context_parts else "No tools called."

            return SkillResult(
                success=True,
                skill_name=skill.name,
                data={
                    "topic": topic,
                    "style": style,
                    "platform": platform,
                    "search_context": search_context,
                    "llm_plan": plan,
                },
                tool_calls=tool_calls,
            )

        except Exception as e:
            return SkillResult(
                success=False,
                skill_name=skill.name,
                error_message=f"LLM-driven execution failed: {e}",
            )


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


class LLMDrivenSkill(Skill):
    """A skill whose tool execution order is determined by an LLM.

    Subclasses only need to define name, description, and required_tools.
    The LLM decides which tools to call, with what args, and in what order.
    """

    workflow_type: str = "llm_driven"

    # Default: use base execute, which is handled by SkillRegistry._execute_llm_driven
    def execute(self, registry: ToolRegistry, params: dict) -> SkillResult:
        """This is a placeholder — actual execution handled by SkillRegistry."""
        return SkillResult(
            success=True,
            skill_name=self.name,
            data={"topic": params.get("topic", "")},
        )


class ResearchAndWriteSkill(LLMDrivenSkill):
    """Research + write — LLM decides whether to search, use RAG, or both."""

    name = "research_and_write"
    description = "研究并撰写内容：根据话题决定搜索、时间检查、RAG 检索等工具的组合"
    required_tools = ["web_search", "get_current_time"]


# All built-in skills for automatic registration
BUILTIN_SKILLS: list[type[Skill]] = [
    TrendingWritingSkill,
    TechnicalArticleSkill,
    ThreadWritingSkill,
    ResearchAndWriteSkill,  # v0.4: LLM-driven skill
]
