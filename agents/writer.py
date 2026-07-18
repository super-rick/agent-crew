"""
Writer Agent — AI 文案员工。

负责：
1. 内容策略（选话题、选风格）
2. 内容生成（调用 LLM + RAG 上下文 + Skill 编排）
3. 多平台格式适配

核心流程:
    execute(task) →
      _enrich_context(topic)  // RAG 检索 + Web 搜索
      _build_messages()       // 组装 system + context + user prompt
      llm.chat(messages)      // 调用 DeepSeek
      format_for_platform()   // 按平台格式化
      return ContentResult
"""

from __future__ import annotations

from datetime import datetime

from agents.base import BaseAgent, Task, TaskResult
from agents.skills import BUILTIN_SKILLS, SkillRegistry
from agents.tools import BUILTIN_TOOLS, ToolRegistry
from llm.client import LLMClient
from rag.knowledge_base import KnowledgeBase
from rag.retriever import Retriever


class WriterAgent(BaseAgent):
    """Content generation agent — the AI copywriter employee."""

    name = "writer"
    description = "负责内容策略和文案生成，掌握追热点、技术文章、Thread 写作等技能"

    def __init__(
        self,
        llm_client: LLMClient,
        config: dict | None = None,
        kb: KnowledgeBase | None = None,
    ):
        super().__init__(llm_client, config)
        self.kb = kb
        self.retriever = Retriever(kb) if kb else None
        self.content_templates: dict = {}

        # Initialize Tool and Skill registries
        self._tool_registry = ToolRegistry()
        self._skill_registry = SkillRegistry()

        # Register built-in tools
        for tool in BUILTIN_TOOLS:
            self._tool_registry.register(tool)

        # Register built-in skills
        for skill_class in BUILTIN_SKILLS:
            self._skill_registry.register(skill_class)

        # Writer-specific content templates
        self.content_templates = {
            "technical": "技术深度文章，结构清晰，带示例代码",
            "casual": "轻松友好的科普帖，用比喻解释概念",
            "thread": "多帖 Thread，每帖一个要点，有钩子",
            "promotional": "推广型内容，突出项目价值和使用场景",
        }

    def get_system_prompt(self) -> str:
        """Load the writer system prompt from file or use default."""
        prompt_path = self.config.get("writer_system_prompt", "configs/prompts/writer_system.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        return (
            "你是一个专业的技术内容创作者。"
            "你用中文为开发者社区撰写高质量的技术文章和推广内容。"
            "你的文风简洁、结构化、有深度。"
            "你会根据目标平台调整格式和语气。"
        )

    def execute(self, task: Task) -> TaskResult:
        """Execute a writing task.

        Task params:
            topic (str): 写作主题
            style (str): technical / casual / thread / promotional
            platform (str): juejin / zhihu / twitter / generic
            skill (str, optional): trending_writing / technical_article / thread_writing
            enable_rag (bool): 是否使用 RAG 检索上下文
            project_info (str, optional): 项目/产品描述，注入到写作 prompt
            word_count (str, optional): auto / short / medium / long
        """
        started_at = datetime.now()
        topic = task.params.get("topic", task.params.get("title", ""))
        style = task.params.get("style", "technical")
        platform = task.params.get("platform", "generic")
        skill_name = task.params.get("skill", "")
        enable_rag = task.params.get("enable_rag", True)
        project_info = task.params.get("project_info", "")
        word_count = task.params.get("word_count", "auto")

        try:
            # Step 1: Run skill enrichment if a skill is specified
            skill_context = {}
            if skill_name and skill_name in self._skill_registry.list_names():
                skill_result = self._skill_registry.execute(
                    skill_name, self._tool_registry, task.params
                )
                if skill_result.success and skill_result.data:
                    skill_context = skill_result.data

            # Step 2: RAG context enrichment
            rag_context = ""
            if enable_rag and self.retriever:
                results = self.retriever.retrieve_for_writing(topic=topic, style=style, limit=3)
                rag_context = self.retriever.format_context(results)

            # Step 3: Build the LLM prompt
            user_prompt = self._build_writing_prompt(
                topic=topic,
                style=style,
                platform=platform,
                skill_context=skill_context,
                rag_context=rag_context,
                project_info=project_info,
                word_count=word_count,
            )

            # Step 4: Call LLM
            messages = self._build_messages(user_prompt)
            content = self.llm_client.chat(messages)

            # Step 5: Format for platform
            formatted = self.format_for_platform(content, platform)

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            return TaskResult(
                task_id=task.task_id,
                success=True,
                data={
                    "topic": topic,
                    "style": style,
                    "platform": platform,
                    "raw_content": content,
                    "formatted_content": formatted,
                    "word_count": len(content),
                    "skill_used": skill_name or "none",
                    "rag_used": enable_rag and bool(rag_context),
                },
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                agent_name=self.name,
            )

        except Exception as e:
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error_message=str(e),
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                agent_name=self.name,
            )

    def _build_writing_prompt(
        self,
        topic: str,
        style: str,
        platform: str,
        skill_context: dict,
        rag_context: str,
        project_info: str,
        word_count: str,
    ) -> str:
        """Build the user prompt for content generation."""
        style_guide = self.content_templates.get(style, style)

        platform_notes = {
            "juejin": "掘金风格：技术深度文章，Markdown 格式，带示例代码，4000-8000字",
            "zhihu": "知乎风格：回答式，有明确观点，能引发讨论，800-3000字",
            "twitter": "X/Twitter 风格：短小精悍 Thread，每条<280字符，有钩子",
            "generic": "通用风格：适合发布到博客或个人网站",
        }

        parts = [f"## 写作任务\n话题: {topic}\n风格: {style_guide}\n目标平台: {platform}"]

        # Inject project info if provided
        if project_info:
            parts.append(
                f"\n## 项目信息\n以下是你需要推广的产品/项目信息，请严格基于这些信息写作：\n{project_info}"  # noqa: E501
            )

        notes = platform_notes.get(platform, platform_notes["generic"])
        parts.append(f"\n格式要求: {notes}")

        if word_count != "auto":
            counts = {"short": "300-500", "medium": "1000-2000", "long": "3000-6000"}
            parts.append(f"\n字数: {counts.get(word_count, 'auto')}")

        if rag_context and rag_context != "（知识库中未找到相关内容）":
            parts.append(f"\n{rag_context}")

        if skill_context.get("search_context"):
            parts.append(f"\n## 搜索参考\n{skill_context['search_context']}")

        parts.append(
            "\n\n请生成完整内容。不要只写大纲，请输出完整文章。"
            '不得包含"抱歉，我无法生成完整内容"类回复。'
        )

        return "\n".join(parts)

    def format_for_platform(self, content: str, platform: str) -> str:
        """Apply platform-specific formatting rules."""
        if platform == "twitter":
            return self._format_as_thread(content)
        if platform == "juejin":
            return self._format_as_article(content)
        if platform == "zhihu":
            return self._format_as_answer(content)
        return content

    def _format_as_thread(self, content: str) -> str:
        """Split long content into Twitter thread posts."""
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        thread = []
        current = []
        char_count = 0

        for line in lines:
            if char_count + len(line) > 260:
                thread.append("\n".join(current))
                current = [line]
                char_count = len(line)
            else:
                current.append(line)
                char_count += len(line)

        if current:
            thread.append("\n".join(current))

        return "\n\n---\n\n".join(f"🧵 {i+1}/{len(thread)}\n{t}" for i, t in enumerate(thread))

    def _format_as_article(self, content: str) -> str:
        """Format as a Juejin-style technical article (Markdown)."""
        return content.strip()

    def _format_as_answer(self, content: str) -> str:
        """Format as a Zhihu-style answer."""
        return content.strip()

    def generate_outline(self, topic: str, style: str = "technical") -> str:
        """Generate a content outline without writing the full article."""
        prompt = (
            f"为以下话题生成一个详细的内容大纲：{topic}\n"
            f"风格: {style}\n"
            f"要求：包含标题、各小节的要点、核心观点、结尾互动引导"
        )
        messages = self._build_messages(prompt)
        return self.llm_client.chat(messages)

    def compose_article(
        self,
        topic: str,
        style: str = "technical",
        platform: str = "generic",
        enable_rag: bool = True,
    ) -> str:
        """Convenience method: generate an article synchronously."""
        task = Task(
            task_id=f"write_{datetime.now().timestamp()}",
            task_type="write",
            params={
                "topic": topic,
                "style": style,
                "platform": platform,
                "enable_rag": enable_rag,
            },
        )
        result = self.execute(task)
        if result.success:
            return result.data.get("formatted_content", result.data.get("raw_content", ""))
        return f"Error: {result.error_message}"
