"""
Medium platform adapter.

Medium.com is a popular international blogging platform.
Supports API key authentication and article publishing.

Auth: API key (from Medium Settings → Integration tokens)
API docs: https://github.com/Medium/medium-api-docs
"""

from __future__ import annotations

from typing import Any

import httpx

from platforms.base import BasePlatformAdapter, ContentPost, PlatformStatus, PostResult


class MediumAdapter(BasePlatformAdapter):
    """Medium adapter — API key auth, article publishing."""

    platform_name = "medium"
    rate_limit_per_hour = 30
    supports_media = False
    supports_scheduling = False

    API_BASE = "https://api.medium.com/v1"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._api_key: str = ""
        self._user_id: str = ""
        self._client: httpx.Client | None = None

    def authenticate(self) -> bool:
        """Authenticate with Medium API key."""
        self._api_key = self.config.get("api_key", "")
        if not self._api_key:
            self._authenticated = False
            return False

        if self._client is not None:
            self._client.close()
            self._client = None

        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "User-Agent": "AgentCrew-MCN/0.5",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        try:
            resp = self._client.get(f"{self.API_BASE}/me")
            if resp.status_code == 200:
                data = resp.json()
                self._user_id = data.get("data", {}).get("id", "")
                self._authenticated = True
                return True
        except Exception:
            pass

        self._authenticated = False
        return False

    def post(self, content: ContentPost) -> PostResult:
        """Publish an article to Medium."""
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

        title = content.title or "Untitled"
        try:
            resp = self._client.post(
                f"{self.API_BASE}/users/{self._user_id}/posts",
                json={
                    "title": title,
                    "contentFormat": "markdown",
                    "content": content.text,
                    "tags": content.hashtags or [],
                    "publishStatus": "public",
                },
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                post_data = data.get("data", {})
                return PostResult(
                    success=True,
                    platform=self.platform_name,
                    post_id=post_data.get("id", ""),
                    post_url=post_data.get("url", ""),
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
        """Validate content for Medium constraints."""
        if not content.text or not content.text.strip():
            return False, "Content text is empty"

        if content.title and len(content.title) > 200:
            return False, f"Title too long: {len(content.title)} > 200 chars"

        return True, ""

    def get_status(self) -> PlatformStatus:
        return PlatformStatus(
            platform=self.platform_name,
            is_authenticated=self._authenticated,
        )
