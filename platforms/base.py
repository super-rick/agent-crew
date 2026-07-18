"""
Platform adapter base — abstract interface for all social platforms.

每个平台适配器是一个可插拔的组件，实现统一的 post() 接口。
Publisher Agent 通过这个抽象层适配任意平台。

平台适配模式：
- 有官方 API 的平台（掘金、X/Twitter）→ 直接 HTTP API
- 无官方 API 的平台（知乎）→ Playwright 浏览器自动化
- 微信/小红书 → v2 路线图
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ContentPost:
    """Standardized content to be posted to a platform."""

    text: str
    title: str | None = None
    media_urls: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    reply_to_id: str | None = None
    scheduled_at: datetime | None = None


@dataclass
class PostResult:
    """Result of a single post operation."""

    success: bool
    platform: str
    post_id: str | None = None
    post_url: str | None = None
    error_message: str | None = None
    posted_at: datetime = field(default_factory=datetime.now)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "platform": self.platform,
            "post_id": self.post_id,
            "post_url": self.post_url,
            "error_message": self.error_message,
            "posted_at": self.posted_at.isoformat(),
            "metrics": self.metrics,
        }


@dataclass
class PlatformStatus:
    """Connection and quota status for a platform."""

    platform: str
    is_authenticated: bool
    rate_limit_remaining: int = 0
    rate_limit_total: int = 0
    last_posted_at: datetime | None = None
    error_message: str | None = None


class BasePlatformAdapter(ABC):
    """Abstract base class for all platform adapters.

    Subclasses must implement:
        platform_name: str — unique platform identifier
        authenticate() -> bool — establish API connection
        post(content: ContentPost) -> PostResult — publish content
    """

    platform_name: str = "base"
    rate_limit_per_hour: int = 999
    supports_media: bool = False
    supports_scheduling: bool = False

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._authenticated = False

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform.

        Returns True if authentication succeeded.
        """

    @abstractmethod
    def post(self, content: ContentPost) -> PostResult:
        """Post content to the platform.

        Returns a PostResult with the outcome.
        """

    def get_status(self) -> PlatformStatus:
        """Return current connection status and rate limit info."""
        return PlatformStatus(
            platform=self.platform_name,
            is_authenticated=self._authenticated,
        )

    def validate_content(self, content: ContentPost) -> tuple[bool, str]:
        """Validate content against platform constraints.

        Returns (is_valid, error_message).
        Override in platform-specific adapters.
        """
        if not content.text or not content.text.strip():
            return False, "Content text is empty"
        return True, ""

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(platform={self.platform_name}, "
            f"auth={self._authenticated})"
        )
