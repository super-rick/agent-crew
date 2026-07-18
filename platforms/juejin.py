"""
掘金 (Juejin) platform adapter.

掘金有官方 API，通过 Cookie 认证。
支持：发布文章、发布沸点（短内容）、获取文章数据。

API endpoint: https://api.juejin.cn/content_api/v1/article/publish
认证方式: Cookie（用户在浏览器登录后导出）
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from platforms.base import BasePlatformAdapter, ContentPost, PlatformStatus, PostResult


class JuejinAdapter(BasePlatformAdapter):
    """掘金平台适配器 — Cookie 认证，支持文章和沸点发布."""

    platform_name = "juejin"
    rate_limit_per_hour = 10
    supports_media = False
    supports_scheduling = False

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._cookie: str = ""
        self._csrf_token: str = ""
        self._client: httpx.Client | None = None

    def authenticate(self) -> bool:
        """Authenticate via Cookie.

        Cookie 从浏览器登录掘金后导出（开发者工具 → Application → Cookies）。
        需要的 keys: sessionid, session_token
        """
        self._cookie = self.config.get("cookie", "")

        if not self._cookie:
            self._authenticated = False
            return False

        self._client = httpx.Client(
            headers={
                "Cookie": self._cookie,
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Content-Type": "application/json",
                "Origin": "https://juejin.cn",
                "Referer": "https://juejin.cn/",
            },
            timeout=15,
        )

        # Verify by checking the user info endpoint
        try:
            resp = self._client.get(
                "https://api.juejin.cn/user_api/v1/user/get",
            )
            if resp.status_code == 200 and resp.json().get("err_no") == 0:
                self._authenticated = True
                return True
            else:
                self._authenticated = False
                return False
        except Exception:
            self._authenticated = False
            return False

    def post(self, content: ContentPost) -> PostResult:
        """Post an article to 掘金.

        如果 content.title 存在，发布为文章；否则发布为沸点。
        """
        if not self._authenticated and not self.authenticate():
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message="掘金认证失败，请检查 Cookie 是否有效",
            )

        if content.title:
            return self._post_article(content)
        else:
            return self._post_pin(content)

    def _post_article(self, content: ContentPost) -> PostResult:
        """Post a full article to 掘金.

        掘金 API 为两步流程：
        1. 创建草稿 (article_draft/create)
        2. 发布草稿 (article/publish)
        """
        brief = content.text[:80].replace("\n", " ").strip()

        create_payload = {
            "tag_ids": ["6809640448827588622"],  # Python 标签
            "title": content.title or content.text[:50],
            "brief_content": brief,
            "mark_content": content.text,
            "category_id": "6809637769959178254",  # 后端
            "edit_type": 10,  # Markdown 编辑器
            "cover_image": "",
            "link_url": "",
            "theme_ids": [],
        }

        try:
            # Step 1: Create draft
            resp = self._client.post(
                "https://api.juejin.cn/content_api/v1/article_draft/create",
                json=create_payload,
            )
            data = resp.json()

            if data.get("err_no") != 0:
                return PostResult(
                    success=False,
                    platform=self.platform_name,
                    error_message=f"创建草稿失败: {data.get('err_msg', '未知错误')}",
                )

            draft_id = data.get("data", {}).get("draft_id", {}).get("draft_id", "")
            if not draft_id:
                draft_id = str(data.get("data", {}).get("id", ""))

            # Step 2: Publish draft
            publish_payload = {
                "draft_id": draft_id,
                "sync_to_org": False,
                "column_ids": [],
                "theme_ids": [],
            }

            resp = self._client.post(
                "https://api.juejin.cn/content_api/v1/article/publish",
                json=publish_payload,
            )
            data = resp.json()

            if data.get("err_no") == 0:
                article_id = data.get("data", {}).get("article_id", "")
                return PostResult(
                    success=True,
                    platform=self.platform_name,
                    post_id=article_id,
                    post_url=f"https://juejin.cn/post/{article_id}",
                    posted_at=datetime.now(),
                )
            else:
                return PostResult(
                    success=False,
                    platform=self.platform_name,
                    error_message=f"发布失败: {data.get('err_msg', '未知错误')}",
                )
        except Exception as e:
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message=f"请求异常: {str(e)}",
            )

    def _post_pin(self, content: ContentPost) -> PostResult:
        """Post a 沸点 (short post) to 掘金."""
        payload = {
            "content": content.text,
            "visible_level": 1,  # Public
        }

        try:
            resp = self._client.post(
                "https://api.juejin.cn/content_api/v1/pin/publish",
                json=payload,
            )
            data = resp.json()

            if data.get("err_no") == 0:
                pin_id = data.get("data", {}).get("pin_id", "")
                return PostResult(
                    success=True,
                    platform=self.platform_name,
                    post_id=str(pin_id),
                    post_url=f"https://juejin.cn/pin/{pin_id}",
                    posted_at=datetime.now(),
                )
            else:
                return PostResult(
                    success=False,
                    platform=self.platform_name,
                    error_message=f"沸点发布失败: {data.get('err_msg', '未知错误')}",
                )
        except Exception as e:
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message=f"请求异常: {str(e)}",
            )

    def validate_content(self, content: ContentPost) -> tuple[bool, str]:
        """掘金内容验证：文章至少 100 字，沸点至少 10 字."""
        if content.title and len(content.text) < 100:
            return False, "掘金文章正文至少需要 100 字"
        if not content.title and len(content.text) < 10:
            return False, "掘金沸点至少需要 10 字"
        return True, ""

    def get_status(self) -> PlatformStatus:
        """Check current auth status and rate limit info."""
        return PlatformStatus(
            platform=self.platform_name,
            is_authenticated=self._authenticated,
            rate_limit_remaining=self.rate_limit_per_hour,
            rate_limit_total=self.rate_limit_per_hour,
        )
