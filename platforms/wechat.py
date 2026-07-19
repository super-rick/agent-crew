"""
WeChat Public Platform adapter.

WeChat (微信公众号) is China's largest content ecosystem.
Supports OAuth authentication via AppID + AppSecret → access_token.

Auth: AppID + AppSecret (from mp.weixin.qq.com backend)
API docs: https://developers.weixin.qq.com/doc/offiaccount/
"""

from __future__ import annotations

from typing import Any

import httpx

from platforms.base import BasePlatformAdapter, ContentPost, PlatformStatus, PostResult


class WechatAdapter(BasePlatformAdapter):
    """WeChat Public Platform adapter — AppID/Secret OAuth."""

    platform_name = "wechat"
    rate_limit_per_hour = 10
    supports_media = True  # Images via material management API
    supports_scheduling = False

    API_BASE = "https://api.weixin.qq.com"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._app_id: str = ""
        self._app_secret: str = ""
        self._access_token: str = ""
        self._client: httpx.Client | None = None

    def authenticate(self) -> bool:
        """Authenticate with WeChat AppID + AppSecret.

        Get credentials from: https://mp.weixin.qq.com → 开发 → 基本配置
        """
        self._app_id = self.config.get("app_id", "")
        self._app_secret = self.config.get("app_secret", "")

        if not self._app_id or not self._app_secret:
            self._authenticated = False
            return False

        if self._client is not None:
            self._client.close()
            self._client = None

        self._client = httpx.Client(
            headers={"User-Agent": "AgentCrew-MCN/0.5"},
            timeout=30.0,
        )

        # Get access token
        try:
            resp = self._client.get(
                f"{self.API_BASE}/cgi-bin/token",
                params={
                    "grant_type": "client_credential",
                    "appid": self._app_id,
                    "secret": self._app_secret,
                },
            )
            data = resp.json()
            token = data.get("access_token", "")
            if token:
                self._access_token = token
                self._authenticated = True
                return True
        except Exception:
            pass

        self._authenticated = False
        return False

    def post(self, content: ContentPost) -> PostResult:
        """Publish a draft to WeChat."""
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
            # Step 1: Create draft
            draft_resp = self._client.post(
                f"{self.API_BASE}/cgi-bin/draft/add",
                params={"access_token": self._access_token},
                json={
                    "articles": [
                        {
                            "title": title[:64],  # WeChat title max 64 chars
                            "content": content.text,
                            "content_source_url": "",
                            "need_open_comment": 0,
                        }
                    ]
                },
            )
            draft_data = draft_resp.json()
            media_id = draft_data.get("media_id", "")

            if media_id:
                return PostResult(
                    success=True,
                    platform=self.platform_name,
                    post_id=media_id,
                    post_url=f"https://mp.weixin.qq.com (draft: {media_id})",
                )

            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message=f"Draft creation failed: {draft_data.get('errmsg', 'unknown')}",
            )

        except Exception as e:
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message=str(e),
            )

    def validate_content(self, content: ContentPost) -> tuple[bool, str]:
        """Validate content for WeChat constraints."""
        if not content.text or not content.text.strip():
            return False, "Content text is empty"

        if content.title and len(content.title) > 64:
            return False, f"Title too long: {len(content.title)} > 64 chars"

        if len(content.text) < 300:
            return False, f"Content too short: {len(content.text)} < 300 chars"

        return True, ""

    def get_status(self) -> PlatformStatus:
        """Return current connection status."""
        return PlatformStatus(
            platform=self.platform_name,
            is_authenticated=self._authenticated,
        )
