[:cn: 中文](/zh/platforms/){ .md-button }

# Platform Setup

AgentCrew supports 9 content platforms.

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

## Auth Methods

### Cookie (Juejin, CSDN, SegmentFault, Xiaohongshu)

1. Login to platform in browser
2. F12 → Application → Cookies
3. Copy all Cookie string
4. Set in `.env`

### API Key (Dev.to, Medium)

1. Go to platform settings → generate API key
2. Set in `.env`

### OAuth (WeChat, X/Twitter)

1. Get credentials from developer portal
2. Set in `.env`

### Playwright (Zhihu)

First run requires GUI for manual login. Cookie auto-saved.
