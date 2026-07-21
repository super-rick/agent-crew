"""
CSDN platform adapter.

CSDN (csdn.net) is China's largest developer community.
Supports cookie-based authentication and article publishing.

Auth: Cookie (copy from browser)
API: REST-style endpoints for article CRUD
"""

from __future__ import annotations

from typing import Any

import httpx

from platforms.base import BasePlatformAdapter, ContentPost, PlatformStatus, PostResult


class CsdnAdapter(BasePlatformAdapter):
    """CSDN platform adapter — Cookie auth, API article publishing."""

    platform_name = "csdn"
    rate_limit_per_hour = 20
    supports_media = False
    supports_scheduling = False

    BASE_URL = "https://blog.csdn.net"
    API_URL = "https://mp.csdn.net/api"
    # Fallback API endpoints tried in order when the primary fails with 405
    _POST_ENDPOINTS = [
        "/article/save",
        "/v2/article/save",
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._cookie: str = ""
        self._client: httpx.Client | None = None

    def authenticate(self) -> bool:
        """Authenticate with CSDN cookie.

        Get your cookie from browser DevTools → Application → Cookies → csdn.net
        Copy the entire cookie string (key=value pairs separated by ;).
        CSDN requires a CSRF token extracted from the cookie for API authentication.
        """
        self._cookie = self.config.get("cookie", "")
        if not self._cookie:
            self._authenticated = False
            return False

        if self._client is not None:
            self._client.close()
            self._client = None

        # Extract CSRF token from cookie string (key: csrfToken or CSRF-Token)
        import re

        csrf_token = ""
        for key in ("csrfToken", "CSRF-Token", "XSRF-TOKEN", "csrf_token"):
            m = re.search(rf"{key}=([^;]+)", self._cookie)
            if m:
                csrf_token = m.group(1).strip()
                break

        self._client = httpx.Client(
            headers={
                "Cookie": self._cookie,
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Content-Type": "application/json",
                "Referer": "https://mp.csdn.net/",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                **({"X-CSRF-Token": csrf_token} if csrf_token else {}),
            },
            timeout=30.0,
            follow_redirects=True,
        )

        # Verify auth by checking user info
        try:
            resp = self._client.get(f"{self.API_URL}/user/info")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 200:
                    self._authenticated = True
                    return True
        except Exception:
            pass

        self._authenticated = False
        return False

    def post(self, content: ContentPost) -> PostResult:
        """Publish an article to CSDN."""
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
        payload = {
            "title": title,
            "content": content.text,
            "markdowncontent": content.text,
            "tags": ",".join(content.hashtags) if content.hashtags else "",
            "type": "original",
            "status": 2,  # 2 = published
        }
        last_error = ""

        try:
            for endpoint in self._POST_ENDPOINTS:
                url = f"{self.API_URL}{endpoint}"
                resp = self._client.post(url, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == 200:
                        article_id = str(data.get("data", {}).get("id", ""))
                        return PostResult(
                            success=True,
                            platform=self.platform_name,
                            post_id=article_id,
                            post_url=f"{self.BASE_URL}/{article_id}" if article_id else "",
                        )
                    last_error = f"API error: {data.get('message', resp.text[:200])}"
                elif resp.status_code == 405:
                    continue  # Try next endpoint
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"

            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message=last_error or "All API endpoints failed",
            )

        except Exception as e:
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message=str(e),
            )

    def validate_content(self, content: ContentPost) -> tuple[bool, str]:
        """Validate content for CSDN platform constraints."""
        if not content.text or not content.text.strip():
            return False, "Content text is empty"

        if content.title and len(content.title) > 100:
            return False, f"Title too long: {len(content.title)} > 100 chars"

        if len(content.text) < 200:
            return False, f"Content too short: {len(content.text)} < 200 chars"

        return True, ""

    def get_status(self) -> PlatformStatus:
        """Return current connection status."""
        return PlatformStatus(
            platform=self.platform_name,
            is_authenticated=self._authenticated,
        )
