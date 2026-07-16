from __future__ import annotations
"""
知乎 (Zhihu) platform adapter.

知乎没有公开的发布 API，使用 Playwright 浏览器自动化。
通过 Cookie 持久化保持登录状态。

Authentication: Cookie（用户在浏览器登录后导出）
Posting: Playwright 浏览器自动化
Anti-detection: 随机延迟、人类行为模拟
"""

import json
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from platforms.base import BasePlatformAdapter, ContentPost, PostResult, PlatformStatus


class ZhihuAdapter(BasePlatformAdapter):
    """知乎平台适配器 — Playwright 浏览器自动化 + Cookie 持久化."""

    platform_name = "zhihu"
    rate_limit_per_hour = 5  # 模拟人类频率，避免被检测
    supports_media = True
    supports_scheduling = False

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._cookie_str: str = ""
        self._cookie_file: str = config.get("cookie_file", "data/zhihu_cookies.json") if config else "data/zhihu_cookies.json"
        self._browser = None
        self._context = None
        self._page = None

    def authenticate(self) -> bool:
        """加载 Cookie 并验证知乎登录状态。

        Cookie 从浏览器登录知乎后导出（开发者工具 → Application → Cookies）。
        支持的格式: 直接从环境变量读取的 Cookie 字符串，或从本地文件加载。
        """
        self._cookie_str = self.config.get("cookie", "") if self.config else ""

        # Try loading from file if no cookie in config
        if not self._cookie_str:
            cookie_file_path = Path(self._cookie_file)
            if cookie_file_path.exists():
                with open(cookie_file_path, "r", encoding="utf-8") as f:
                    self._cookie_str = f.read().strip()

        if not self._cookie_str:
            self._authenticated = False
            return False

        # Verify with a simple HTTP check first (no need to launch Playwright)
        import httpx

        try:
            resp = httpx.get(
                "https://www.zhihu.com/api/v4/me",
                headers={
                    "Cookie": self._cookie_str,
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
                timeout=10,
            )
            if resp.status_code == 200:
                self._authenticated = True
                return True
        except Exception:
            pass

        self._authenticated = False
        return False

    async def _ensure_browser(self):
        """Lazy-init Playwright browser."""
        if self._browser is not None:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is required for Zhihu adapter. "
                "Install: pip install playwright && playwright install chromium"
            )

        p = await async_playwright().__aenter__()
        self._browser = await p.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
        )

        # Load saved browser state (cookies + localStorage)
        cookie_file = Path(self._cookie_file)
        if cookie_file.exists():
            await self._context.add_cookies(
                self._parse_cookie_file(cookie_file)
            )
        elif self._cookie_str:
            cookies = self._parse_cookies(self._cookie_str)
            if cookies:
                await self._context.add_cookies(cookies)

        self._page = await self._context.new_page()

    @staticmethod
    def _markdown_to_html(text: str) -> str:
        """Convert Markdown to HTML suitable for Zhihu's Draft.js editor.

        Code blocks are rendered with inline styling so they display correctly
        without requiring external CSS (which Zhihu strips).
        """
        import re
        import markdown as md_lib

        # First, protect fenced code blocks from markdown processing
        # by converting them to HTML <pre> blocks with inline styling
        CODE_STYLE = (
            "background:#f6f8fa;border-radius:6px;padding:16px;"
            "overflow-x:auto;font-family:'SF Mono',Monaco,Menlo,monospace;"
            "font-size:14px;line-height:1.8;color:#24292e;"
            "margin:16px 0;display:block;border:1px solid #e1e4e8;"
            "white-space:pre;word-wrap:normal;"
        )

        def _replace_fenced_code(match):
            lang = match.group(1) or ""
            code = match.group(2)
            # Escape HTML entities (do this BEFORE whitespace conversion)
            code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Convert spaces to &nbsp; to preserve indentation in Draft.js
            code = code.replace("  ", "&nbsp;&nbsp;")
            lang_label = f'<span style="color:#6a737d;font-size:12px;display:block;margin-bottom:8px;">{lang}</span>' if lang else ""
            # Use <div> instead of <pre> — Draft.js handles it better for whitespace
            return f'<div style="{CODE_STYLE}">{lang_label}{code}</div>'

        # Replace ```code``` blocks
        text = re.sub(r"```(\w*)\n(.*?)```", _replace_fenced_code, text, flags=re.DOTALL)

        # Replace inline `code` spans
        INLINE_STYLE = (
            "background:#f0f0f0;padding:2px 6px;border-radius:3px;"
            "font-family:'SF Mono',Monaco,Menlo,monospace;font-size:13px;"
            "color:#e83e8c;"
        )
        text = re.sub(
            r"`([^`]+?)`",
            lambda m: f'<code style="{INLINE_STYLE}">{m.group(1)}</code>',
            text,
        )

        # Convert remaining Markdown to HTML
        html = md_lib.markdown(
            text,
            extensions=["fenced_code", "tables"],
        )

        # Wrap in a container with proper line-height for readability
        return f'<div style="line-height:1.8;color:#1a1a1a;">{html}</div>'

    def _parse_cookie_file(self, cookie_file: Path) -> list[dict]:
        """Parse saved browser state (from auth command) into Playwright cookie format."""
        data = json.loads(cookie_file.read_text(encoding="utf-8"))
        # Playwright storage_state format: {"cookies": [...], "origins": [...]}
        if "cookies" in data and isinstance(data["cookies"], list):
            return data["cookies"]
        return []

    def _parse_cookies(self, cookie_str: str) -> list[dict]:
        """Parse Cookie header string into Playwright cookie format."""
        cookies = []
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                name, value = item.split("=", 1)
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".zhihu.com",
                    "path": "/",
                })
        return cookies

    def _random_delay(self, min_ms: int = 800, max_ms: int = 3000):
        """随机延迟，模拟人类操作."""
        import asyncio
        return asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))

    async def _post_async(self, content: ContentPost) -> PostResult:
        """Async posting to 知乎 — the actual Playwright workflow."""
        await self._ensure_browser()
        page = self._page

        try:
            if content.title:
                # Post as article
                await page.goto(
                    "https://zhuanlan.zhihu.com/write",
                    wait_until="networkidle",
                )
                await self._random_delay()

                # Fill title
                title_input = page.locator("textarea[placeholder*='标题']")
                await title_input.fill(content.title)
                await self._random_delay()

                # Try importing Markdown file via Zhihu's built-in importer
                # Write content to a temp .md file for upload
                import tempfile
                _tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".md", encoding="utf-8", delete=False
                )
                _tmp.write(content.text)
                _tmp.close()

                try:
                    # Click "导入文章" in the toolbar if available
                    import_btn = page.locator("text=导入文章")
                    if await import_btn.count() > 0:
                        await import_btn.first.click()
                        await self._random_delay(500, 1000)

                        # Look for file input (hidden) and upload
                        file_input = page.locator('input[type="file"][accept*=".md"], input[type="file"][accept*="markdown"]')
                        if await file_input.count() == 0:
                            # Fallback: generic file input in the import dialog
                            file_input = page.locator('input[type="file"]').first

                        await file_input.set_input_files(_tmp.name)
                        await self._random_delay(3000, 5000)
                    else:
                        # Fallback: type Markdown directly into the editor
                        content_area = page.locator(".public-DraftEditor-content")
                        await content_area.click()
                        await page.keyboard.type(content.title or "", delay=30)
                        await page.keyboard.press("Enter")
                        await page.keyboard.type(content.text, delay=10)
                        await self._random_delay(2000, 4000)
                finally:
                    Path(_tmp.name).unlink(missing_ok=True)

                if content.draft:
                    # Save as draft — content auto-saves, just don't click publish
                    return PostResult(
                        success=True,
                        platform=self.platform_name,
                        post_url="[DRAFT] 已保存到知乎草稿箱",
                        posted_at=datetime.now(),
                    )
                else:
                    # Click publish (use exact match to avoid "发布设置" button)
                    publish_btn = page.get_by_role("button", name="发布", exact=True)
                    await publish_btn.click()
                    await self._random_delay(3000, 5000)

                    current_url = page.url
                    return PostResult(
                        success=True,
                        platform=self.platform_name,
                        post_url=current_url,
                        posted_at=datetime.now(),
                    )
            else:
                # Post as answer (需要指定问题 ID)
                # 简化版: 创建想法（类似沸点）
                await page.goto(
                    "https://www.zhihu.com/creator",
                    wait_until="networkidle",
                )
                await self._random_delay()

                return PostResult(
                    success=False,
                    platform=self.platform_name,
                    error_message="知乎想法发布暂未支持，请使用文章模式",
                )

        except Exception as e:
            return PostResult(
                success=False,
                platform=self.platform_name,
                error_message=f"知乎发布异常: {str(e)}",
            )

    def post(self, content: ContentPost) -> PostResult:
        """Synchronous wrapper for the async posting method."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're already in an event loop; create a new one
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(self._post_async(content))
                loop.close()
                return result
            else:
                return loop.run_until_complete(self._post_async(content))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(self._post_async(content))
            loop.close()
            return result

    def validate_content(self, content: ContentPost) -> tuple[bool, str]:
        """知乎内容验证：文章至少 200 字."""
        if content.title and len(content.text) < 200:
            return False, "知乎文章正文至少需要 200 字"
        return True, ""

    def get_status(self) -> PlatformStatus:
        """Check current auth status."""
        return PlatformStatus(
            platform=self.platform_name,
            is_authenticated=self._authenticated,
            rate_limit_remaining=self.rate_limit_per_hour,
            rate_limit_total=self.rate_limit_per_hour,
        )
