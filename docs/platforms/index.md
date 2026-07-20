# Platform Setup

AgentCrew supports 9 content platforms. Each requires different authentication.

## .env Quick Reference

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

## Auth by Type

### Cookie (Juejin, CSDN, SegmentFault, Xiaohongshu)
1. Login in browser → F12 → Application → Cookies → copy all
2. Set in `.env`

### API Key (Dev.to, Medium)
1. Platform settings → Developer → generate key
2. Set in `.env`

### OAuth (WeChat, X/Twitter)
1. Developer portal → get credentials
2. Set in `.env`

### Playwright (Zhihu)
First run opens browser for login. Cookies auto-saved.

## Platforms

- [Juejin](juejin.md) · [Zhihu](zhihu.md) · [Dev.to](devto.md)
- [CSDN](csdn.md) · [WeChat](wechat.md) · [SegmentFault](segmentfault.md)
- [X/Twitter](twitter.md) · [Xiaohongshu](xiaohongshu.md) · [Medium](medium.md)
