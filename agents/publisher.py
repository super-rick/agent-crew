"""
Publisher Agent — AI 运营员工。

负责：
1. 平台适配器注册和管理
2. 跨平台内容发布（单发 / 多发）
3. 内容合规性验证
4. 发布结果记录

核心流程：
    execute(task) →
      对每个目标平台:
        adapter.validate_content()
        adapter.post()
        post_result → task_history
      返回汇总的发布结果
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from agents.base import BaseAgent, Task, TaskResult
from llm.client import LLMClient
from platforms.base import BasePlatformAdapter, ContentPost, PostResult


class PublisherAgent(BaseAgent):
    """Content distribution agent — the AI operations employee."""

    name = "publisher"
    description = "负责将内容分发到多个社交媒体平台，支持定时发布和批量发布"

    # All known platform adapters (including future/planned ones).
    # Used by `publish status` to show full platform coverage.
    KNOWN_PLATFORM_INFO: dict[str, str] = {
        "juejin": "掘金 — Cookie 认证",
        "zhihu": "知乎 — Playwright 浏览器自动化",
        "devto": "Dev.to — Forem API",
        "csdn": "CSDN — 待实现",
        "wechat": "微信公众号 — 待实现",
        "segmentfault": "SegmentFault — 待实现",
        "twitter": "X/Twitter — Twitter API v2",
        "xiaohongshu": "小红书 — 待实现",
        "medium": "Medium — Medium API",
    }

    def __init__(self, llm_client: LLMClient, config: dict | None = None):
        super().__init__(llm_client, config)
        self._platforms: dict[str, BasePlatformAdapter] = {}
        self._history_file: str = (
            config.get("history_file", "data/post_history.json")
            if config
            else "data/post_history.json"
        )
        self._post_history: list[dict] = self._load_history()

    def register_platform(self, name: str, adapter: BasePlatformAdapter) -> None:
        """Register a platform adapter."""
        self._platforms[name] = adapter

    def get_platform(self, name: str) -> BasePlatformAdapter:
        """Get a registered platform adapter by name."""
        if name not in self._platforms:
            available = ", ".join(self._platforms.keys())
            raise KeyError(f"Platform '{name}' not registered. Available: {available}")
        return self._platforms[name]

    def list_platforms(self) -> list[str]:
        """Return names of all registered platforms."""
        return list(self._platforms.keys())

    def get_system_prompt(self) -> str:
        return (
            "你是一个内容分发运营人员。"
            "你负责将写好的内容发布到各个社交媒体平台。"
            "你了解各平台的内容规范和发布限制。"
            "你确保内容合规后按计划发布。"
        )

    def execute(self, task: Task) -> TaskResult:
        """Execute a publishing task.

        Task params:
            content (str or dict): 要发布的内容
                - text: 正文
                - title: 文章标题（对掘金等必须）
                - media_urls: 媒体文件URL列表
                - hashtags: 标签列表
            platforms (list[str]): 目标平台列表
            dry_run (bool): 预览模式，不实际发布
            platform_params (dict, optional): 各平台的特定参数
        """
        started_at = datetime.now()
        content_data = task.params.get("content", {})
        platforms = task.params.get("platforms", [])
        dry_run = task.params.get("dry_run", False)

        # Convert string content to ContentPost
        if isinstance(content_data, str):
            content = ContentPost(text=content_data)
        elif isinstance(content_data, dict):
            content = ContentPost(
                text=content_data.get("text", ""),
                title=content_data.get("title"),
                media_urls=content_data.get("media_urls", []),
                hashtags=content_data.get("hashtags", []),
                reply_to_id=content_data.get("reply_to_id"),
                scheduled_at=content_data.get("scheduled_at"),
            )
        else:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error_message="Invalid content format",
                started_at=started_at,
                completed_at=datetime.now(),
                agent_name=self.name,
            )

        # Determine target platforms
        if not platforms:
            platforms = self.config.get("default_platforms", [])

        if not platforms:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error_message="No target platforms specified",
                started_at=started_at,
                completed_at=datetime.now(),
                agent_name=self.name,
            )

        # Publish to each platform
        results: list[PostResult] = []
        all_success = True

        for platform_name in platforms:
            if platform_name not in self._platforms:
                results.append(
                    PostResult(
                        success=False,
                        platform=platform_name,
                        error_message=f"Platform '{platform_name}' not registered",
                    )
                )
                all_success = False
                continue

            adapter = self._platforms[platform_name]

            # Validate content
            is_valid, error_msg = adapter.validate_content(content)
            if not is_valid:
                results.append(
                    PostResult(
                        success=False,
                        platform=platform_name,
                        error_message=error_msg,
                    )
                )
                all_success = False
                continue

            if dry_run:
                # Simulate a successful post in dry-run mode
                results.append(
                    PostResult(
                        success=True,
                        platform=platform_name,
                        post_id="[DRY-RUN]",
                        post_url=f"[DRY-RUN] would post to {platform_name}",
                    )
                )
                continue

            # Authenticate if needed
            try:
                if not adapter._authenticated:
                    adapter.authenticate()

                result = adapter.post(content)
                if not result.success:
                    all_success = False
                results.append(result)

            except Exception as e:
                results.append(
                    PostResult(
                        success=False,
                        platform=platform_name,
                        error_message=str(e),
                    )
                )
                all_success = False

        # Record to history (skip dry-runs to avoid polluting production data)
        post_records = [r.to_dict() for r in results]
        if not dry_run:
            self._post_history.extend(post_records)
            self._save_history()

        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        return TaskResult(
            task_id=task.task_id,
            success=all_success,
            data={
                "dry_run": dry_run,
                "platforms_attempted": platforms,
                "results": post_records,
                "total": len(results),
                "succeeded": sum(1 for r in results if r.success),
                "failed": sum(1 for r in results if not r.success),
            },
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            agent_name=self.name,
        )

    def post_to_platform(
        self,
        text: str,
        platform: str,
        title: str | None = None,
        dry_run: bool = False,
    ) -> PostResult:
        """Convenience method: post a single text to a single platform."""
        content = ContentPost(text=text, title=title)
        task = Task(
            task_id=f"pub_{datetime.now().timestamp()}",
            task_type="publish",
            params={
                "content": {
                    "text": content.text,
                    "title": content.title,
                },
                "platforms": [platform],
                "dry_run": dry_run,
            },
        )
        result = self.execute(task)
        if result.success and result.data.get("results"):
            results = [PostResult(**r) for r in result.data["results"]]
            return results[0]
        return PostResult(
            success=False,
            platform=platform,
            error_message=result.error_message,
        )

    def _load_history(self) -> list[dict]:
        """Load post history from file."""
        path = Path(self._history_file)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save_history(self):
        """Save post history to file."""
        path = Path(self._history_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._post_history[-100:], f, ensure_ascii=False, indent=2)

    def get_post_history(self, limit: int = 20) -> list[dict]:
        """Return recent post history."""
        return self._post_history[-limit:]
