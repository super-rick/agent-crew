"""
X (Twitter) platform adapter.

X/Twitter is a global social media platform, essential for international reach.
Supports OAuth 1.0a authentication and tweet/thread posting via v2 API.

Auth: OAuth 1.0a (API key + secret + access token + secret)
"""

from __future__ import annotations

from typing import Any

import httpx

from platforms.base import BasePlatformAdapter, ContentPost, PlatformStatus, PostResult


class XTwitterAdapter(BasePlatformAdapter):
    """X/Twitter adapter — OAuth 1.0a, tweet/thread posting."""

    platform_name = "twitter"
    rate_limit_per_hour = 50
    supports_media = False
    supports_scheduling = False

    API_BASE = "https://api.twitter.com/2"
    MAX_TWEET_LENGTH = 280

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._api_key: str = ""
        self._api_secret: str = ""
        self._access_token: str = ""
        self._access_secret: str = ""
        self._client: httpx.Client | None = None

    def authenticate(self) -> bool:
        """Authenticate with OAuth 1.0a credentials.

        Get credentials from: https://developer.twitter.com/en/portal/
        """
        self._api_key = self.config.get("api_key", "")
        self._api_secret = self.config.get("api_secret", "")
        self._access_token = self.config.get("access_token", "")
        self._access_secret = self.config.get("access_secret", "")

        if not all([self._api_key, self._api_secret, self._access_token, self._access_secret]):
            self._authenticated = False
            return False

        if self._client is not None:
            self._client.close()
            self._client = None

        self._client = httpx.Client(
            headers={"User-Agent": "AgentCrew-MCN/0.5"},
            timeout=30.0,
        )

        # Verify credentials by fetching user info
        try:
            resp = self._client.get(
                f"{self.API_BASE}/users/me",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            if resp.status_code == 200:
                self._authenticated = True
                return True
        except Exception:
            pass

        self._authenticated = False
        return False

    def post(self, content: ContentPost) -> PostResult:
        """Post a tweet or thread to X/Twitter."""
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

        try:
            # Split into tweets if content exceeds 280 chars
            tweets = self._split_into_tweets(content.text)
            last_tweet_id = None

            for i, tweet_text in enumerate(tweets):
                payload: dict[str, Any] = {"text": tweet_text}
                if last_tweet_id and i > 0:
                    payload["reply"] = {"in_reply_to_tweet_id": last_tweet_id}

                resp = self._client.post(
                    f"{self.API_BASE}/tweets",
                    headers={"Authorization": f"Bearer {self._access_token}"},
                    json=payload,
                )

                if resp.status_code not in (200, 201):
                    return PostResult(
                        success=False,
                        platform=self.platform_name,
                        error_message=(f"Tweet {i+1} failed: {resp.status_code} {resp.text[:200]}"),
                    )

                data = resp.json()
                tweet_id = data.get("data", {}).get("id", "")
                if i == 0:
                    # Use first tweet as post_id
                    last_tweet_id = tweet_id
                if tweet_id and i > 0:
                    last_tweet_id = tweet_id

            return PostResult(
                success=True,
                platform=self.platform_name,
                post_id=str(last_tweet_id) if last_tweet_id else "",
                post_url=(f"https://x.com/i/web/status/{last_tweet_id}" if last_tweet_id else ""),
            )

        except Exception as e:
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message=str(e),
            )

    def _split_into_tweets(self, text: str) -> list[str]:
        """Split long content into tweet-sized chunks (280 chars each)."""
        if len(text) <= self.MAX_TWEET_LENGTH:
            return [text]

        # Reserve space for thread marker
        marker_overhead = 8  # "\n\n🧵 X/Y" worst case

        tweets = []
        limit = self.MAX_TWEET_LENGTH - marker_overhead
        lines = text.split("\n")
        current = ""
        for line in lines:
            if len(current) + len(line) + 1 <= limit:
                current += ("\n" + line) if current else line
            else:
                if current:
                    tweets.append(current)
                current = line[:limit]

        if current:
            tweets.append(current)

        # Add thread numbering (accounted for in overhead above)
        if len(tweets) > 1:
            total = len(tweets)
            tweets = [f"{t}\n\n🧵 {i+1}/{total}" for i, t in enumerate(tweets)]

        return tweets

    def validate_content(self, content: ContentPost) -> tuple[bool, str]:
        """Validate content for X/Twitter constraints."""
        if not content.text or not content.text.strip():
            return False, "Content text is empty"
        if len(content.text) < 10:
            return False, f"Content too short: {len(content.text)} < 10 chars"
        return True, ""

    def get_status(self) -> PlatformStatus:
        return PlatformStatus(
            platform=self.platform_name,
            is_authenticated=self._authenticated,
        )
