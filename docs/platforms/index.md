# Platform Setup

AgentCrew supports 9 content platforms. Each requires different authentication.

## Quick Reference: `.env` Configuration

```bash
# ── LLM (required) ────────────────────────────
DEEPSEEK_API_KEY=sk-your-key-here

# ── Juejin 掘金 ────────────────────────────────
JUEJIN_COOKIE="cookie_from_browser"

# ── Zhihu 知乎 ─────────────────────────────────
# (Playwright browser automation, no env var needed)

# ── Dev.to ─────────────────────────────────────
DEVTO_API_KEY=your-devto-api-key

# ── CSDN ───────────────────────────────────────
CSDN_COOKIE="cookie_from_browser"

# ── WeChat 微信公众号 ──────────────────────────
WECHAT_APP_ID=wx_your_app_id
WECHAT_APP_SECRET=your_app_secret

# ── SegmentFault 思否 ──────────────────────────
SEGMENTFAULT_COOKIE="cookie_from_browser"

# ── X/Twitter ──────────────────────────────────
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret

# ── Xiaohongshu 小红书 ─────────────────────────
XIAOHONGSHU_COOKIE="cookie_from_browser"

# ── Medium ─────────────────────────────────────
MEDIUM_API_KEY=your-medium-api-key
```

## Auth Methods by Type

### Cookie Authentication

**Platforms:** Juejin, CSDN, SegmentFault, Xiaohongshu

1. Login to the platform in your browser
2. Press `F12` → **Application** → **Cookies**
3. Select the platform domain (e.g., `juejin.cn`)
4. Copy all cookies as a single string (key=value; key=value; ...)
5. Paste into `.env` under the corresponding variable

### API Key

**Platforms:** Dev.to, Medium

1. Go to platform settings → **Developer** or **Integration tokens**
2. Generate a new API key
3. Copy into `.env`

- Dev.to: https://dev.to/settings/extensions
- Medium: https://medium.com/me/settings → Integration tokens

### OAuth / Credentials

**Platforms:** WeChat, X/Twitter

1. Go to the developer portal
2. Create an application or get API credentials
3. Copy AppID/Secret or API Key/Secret into `.env`

- WeChat: https://mp.weixin.qq.com → 开发 → 基本配置
- X/Twitter: https://developer.twitter.com/en/portal

### Playwright (Browser Automation)

**Platform:** Zhihu

No `.env` configuration needed. On first use, a browser window opens for you to login manually. Cookies are saved automatically to the `data/` directory for subsequent runs.

## Supported Platforms

- **[Juejin](juejin.md)** (掘金) — Cookie auth, Markdown articles
- **[Zhihu](zhihu.md)** (知乎) — Playwright browser automation
- **[Dev.to](devto.md)** — API key, English developer community
- **[CSDN](csdn.md)** — Cookie auth, China's largest dev community
- **[WeChat](wechat.md)** (微信公众号) — AppID/Secret OAuth, draft publishing
- **[SegmentFault](segmentfault.md)** (思否) — Cookie auth, tech Q&A + blog
- **[X/Twitter](twitter.md)** — OAuth 1.0a, tweet/thread posting
- **[Xiaohongshu](xiaohongshu.md)** (小红书) — Cookie auth, note publishing
- **[Medium](medium.md)** — API key, international blog
