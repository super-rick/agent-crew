"""
Dev.to platform adapter.

Dev.to is a global developer community powered by the Forem platform.
It offers a free, open API for article publishing with API key auth.

API docs: https://developers.forem.com/api
Base URL: https://dev.to/api
Auth: api-key HTTP header
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from platforms.base import BasePlatformAdapter, ContentPost, PlatformStatus, PostResult

logger = logging.getLogger(__name__)


class DevToAdapter(BasePlatformAdapter):
    """Dev.to platform adapter — Forem API, API key auth."""

    platform_name = "devto"
    rate_limit_per_hour = 30  # Generous limit, usually 300/day
    supports_media = False  # Images via Markdown embeds (not direct upload)
    supports_scheduling = False

    BASE_URL = "https://dev.to/api"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._api_key: str = ""
        self._client: httpx.Client | None = None
        self._auth_error: str = ""  # Specific error from last auth attempt

    def authenticate(self) -> bool:
        """Authenticate with Dev.to API key.

        Get your API key at: https://dev.to/settings/extensions
        """
        self._api_key = self.config.get("api_key", "")

        if not self._api_key:
            self._authenticated = False
            return False

        # Close previous client to avoid resource leak on re-auth
        if self._client is not None:
            self._client.close()
            self._client = None

        self._client = httpx.Client(
            headers={
                "api-key": self._api_key,
                "User-Agent": "AgentCrew-MCN/0.2",
                "Content-Type": "application/json",
                "Accept": "application/vnd.forem.api-v1+json",
            },
            base_url=self.BASE_URL,
            timeout=30,
        )

        # Verify API key with retry for transient errors
        for attempt in range(3):
            try:
                resp = self._client.get("/articles/me?per_page=1")
                if resp.status_code == 200:
                    self._authenticated = True
                    self._auth_error = ""
                    return True
                elif resp.status_code == 401:
                    self._auth_error = "API key rejected (401 Unauthorized)"
                    break  # Don't retry real auth failures
                elif resp.status_code == 403:
                    self._auth_error = "API key lacks required permissions (403 Forbidden)"
                    break
                elif resp.status_code == 429:
                    self._auth_error = f"Rate limited (429), attempt {attempt + 1}/3"
                    if attempt < 2:
                        import time

                        time.sleep(2**attempt)  # Exponential backoff: 1s, 2s
                        continue
                else:
                    self._auth_error = f"HTTP {resp.status_code}"
                    if attempt < 2:
                        import time

                        time.sleep(1)
                        continue
            except httpx.TimeoutException:
                self._auth_error = f"Connection timed out (attempt {attempt + 1}/3)"
                if attempt < 2:
                    import time

                    time.sleep(2**attempt)
                    continue
            except httpx.ConnectError:
                self._auth_error = "Cannot connect to dev.to API (network/DNS)"
                if attempt < 2:
                    import time

                    time.sleep(2**attempt)
                    continue
            except Exception as e:
                self._auth_error = f"Unexpected: {type(e).__name__}"
                break

        logger.warning("Dev.to auth failed: %s", self._auth_error)
        self._authenticated = False
        return False

    def post(self, content: ContentPost) -> PostResult:
        """Post an article to Dev.to.

        Dev.to supports Markdown natively — the body_markdown field
        is rendered directly. No format conversion needed.
        """
        if not self._authenticated and not self.authenticate():
            error_msg = self._auth_error or "Dev.to 认证失败，请检查 DEVTO_API_KEY"
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message=f"Dev.to 认证失败: {error_msg}",
            )

        if self._client is None:
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message="Dev.to 客户端未初始化，请先调用 authenticate()",
            )

        # Auto-extract tags from hashtags (strip # prefix)
        tags = [tag.lstrip("#").lower().replace(" ", "") for tag in content.hashtags]
        # Ensure we have at least some tags (max 4 on Dev.to)
        tags = (tags or ["opensource", "python", "ai"])[:4]

        # Build article payload
        title = content.title or content.text[:80].split("\n")[0].strip()
        article = {
            "title": title,
            "body_markdown": content.text,
            "published": True,
            "tags": tags,
        }

        # Add optional description (first 160 chars of text)
        description = content.text[:160].replace("\n", " ").strip()
        if description and description != title:
            article["description"] = description

        try:
            resp = self._client.post("/articles", json={"article": article})
            data = resp.json()

            if resp.status_code in (200, 201):
                article_url = data.get("url", "")
                article_id = str(data.get("id", ""))
                return PostResult(
                    success=True,
                    platform=self.platform_name,
                    post_id=article_id,
                    post_url=article_url,
                    posted_at=datetime.now(),
                )
            else:
                error_msg = data.get("error", "未知错误")
                return PostResult(
                    success=False,
                    platform=self.platform_name,
                    error_message=f"Dev.to 发布失败: {error_msg}",
                )
        except Exception as e:
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message=f"Dev.to 请求异常: {str(e)}",
            )

    def validate_content(self, content: ContentPost) -> tuple[bool, str]:
        """Dev.to content validation: article body must not be empty."""
        if not content.text or not content.text.strip():
            return False, "Dev.to 文章正文不能为空"
        if content.title and len(content.title) > 128:
            return False, "Dev.to 标题不能超过 128 字符"
        return True, ""

    def get_status(self) -> PlatformStatus:
        """Check current auth status and rate limit info."""
        return PlatformStatus(
            platform=self.platform_name,
            is_authenticated=self._authenticated,
            rate_limit_remaining=self.rate_limit_per_hour,
            rate_limit_total=self.rate_limit_per_hour,
        )
