"""
Xiaohongshu (小红书/RED) platform adapter.

Xiaohongshu is a lifestyle sharing platform with strong content community.
Supports cookie-based authentication and note publishing.

Auth: Cookie (copy from browser, login required)
"""

from __future__ import annotations

from typing import Any

import httpx

from platforms.base import BasePlatformAdapter, ContentPost, PlatformStatus, PostResult


class XiaohongshuAdapter(BasePlatformAdapter):
    """Xiaohongshu adapter — Cookie auth, note publishing."""

    platform_name = "xiaohongshu"
    rate_limit_per_hour = 15
    supports_media = True  # Images supported
    supports_scheduling = False

    BASE_URL = "https://www.xiaohongshu.com"
    API_URL = "https://edith.xiaohongshu.com/api"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._cookie: str = ""
        self._client: httpx.Client | None = None

    def authenticate(self) -> bool:
        """Authenticate with Xiaohongshu cookie."""
        self._cookie = self.config.get("cookie", "")
        if not self._cookie:
            self._authenticated = False
            return False

        if self._client is not None:
            self._client.close()
            self._client = None

        self._client = httpx.Client(
            headers={
                "Cookie": self._cookie,
                "User-Agent": "AgentCrew-MCN/0.5",
                "Content-Type": "application/json",
                "Referer": self.BASE_URL,
            },
            timeout=30.0,
            follow_redirects=True,
        )

        try:
            resp = self._client.get(f"{self.API_URL}/web/profile")
            if resp.status_code == 200:
                self._authenticated = True
                return True
        except Exception:
            pass

        self._authenticated = False
        return False

    def post(self, content: ContentPost) -> PostResult:
        """Publish a note to Xiaohongshu."""
        if not self._authenticated or self._client is None:
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message="Not authenticated. Call authenticate() first.",
            )

        if not content.text or not content.text.strip():
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message="Content text is empty",
            )

        title = content.title or content.text[:20]
        try:
            resp = self._client.post(
                f"{self.API_URL}/sns/web/v1/note",
                json={
                    "title": title[:20],
                    "desc": content.text[:1000],  # Note description max ~1000
                    "type": "normal",
                    "images": content.media_urls or [],
                    "topics": content.hashtags or [],
                    "post_locale": "zh-cn",
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    note_id = data.get("data", {}).get("note_id", "")
                    return PostResult(
                        success=True,
                        platform=self.platform_name,
                        post_id=note_id,
                        post_url=(f"{self.BASE_URL}/explore/{note_id}" if note_id else ""),
                    )

            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message=f"API returned {resp.status_code}: {resp.text[:200]}",
            )

        except Exception as e:
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message=str(e),
            )

    def validate_content(self, content: ContentPost) -> tuple[bool, str]:
        """Validate content for Xiaohongshu constraints."""
        if not content.text or not content.text.strip():
            return False, "Content text is empty"

        if content.title and len(content.title) > 20:
            return False, f"Title too long: {len(content.title)} > 20 chars"

        if len(content.text) < 50:
            return False, f"Content too short: {len(content.text)} < 50 chars"

        return True, ""

    def get_status(self) -> PlatformStatus:
        return PlatformStatus(
            platform=self.platform_name,
            is_authenticated=self._authenticated,
        )
