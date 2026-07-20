# 平台配置

AgentCrew 支持 9 个内容平台。每个平台需要不同的认证方式。

## `.env` 配置速查

```bash
# ── LLM（必填）────────────────────────────────
DEEPSEEK_API_KEY=sk-your-key-here

# ── Juejin 掘金 ────────────────────────────────
JUEJIN_COOKIE="从浏览器复制的Cookie"

# ── Zhihu 知乎 ─────────────────────────────────
# (Playwright 浏览器自动化，无需 env 变量)

# ── Dev.to ─────────────────────────────────────
DEVTO_API_KEY=从dev.to获取的api-key

# ── CSDN ───────────────────────────────────────
CSDN_COOKIE="从浏览器复制的Cookie"

# ── WeChat 微信公众号 ──────────────────────────
WECHAT_APP_ID=wx_你的appid
WECHAT_APP_SECRET=你的appsecret

# ── SegmentFault 思否 ──────────────────────────
SEGMENTFAULT_COOKIE="从浏览器复制的Cookie"

# ── X/Twitter ──────────────────────────────────
TWITTER_API_KEY=你的api_key
TWITTER_API_SECRET=你的api_secret
TWITTER_ACCESS_TOKEN=你的access_token
TWITTER_ACCESS_SECRET=你的access_secret

# ── Xiaohongshu 小红书 ─────────────────────────
XIAOHONGSHU_COOKIE="从浏览器复制的Cookie"

# ── Medium ─────────────────────────────────────
MEDIUM_API_KEY=从medium获取的api-key
```

## 认证方式分类

### Cookie 认证

**平台：** 掘金、CSDN、SegmentFault、小红书

1. 浏览器登录目标平台
2. `F12` → **Application** → **Cookies**
3. 选择平台域名（如 `juejin.cn`）
4. 复制所有 Cookie 字符串（`key=value; key=value; ...`）
5. 粘贴到 `.env` 对应变量

### API Key

**平台：** Dev.to、Medium

1. 平台设置页 → Developer / Integration tokens
2. 生成 API key
3. 填入 `.env`

- Dev.to: https://dev.to/settings/extensions
- Medium: https://medium.com/me/settings → Integration tokens

### OAuth / 双密钥

**平台：** 微信公众号、X/Twitter

1. 开发者后台申请凭证
2. 填入 `.env` 对应变量

- 微信: https://mp.weixin.qq.com → 开发 → 基本配置
- X/Twitter: https://developer.twitter.com/en/portal

### Playwright 浏览器

**平台：** 知乎

无需配置 `.env`。首次运行会打开浏览器窗口，手动登录后 Cookie 自动保存到 `data/` 目录。

## 支持的平台

- **[掘金](juejin.md)** — Cookie 认证，Markdown 文章
- **[知乎](zhihu.md)** — Playwright 浏览器自动化
- **[Dev.to](devto.md)** — API key，英文社区
- **[CSDN](csdn.md)** — Cookie 认证
- **[微信公众号](wechat.md)** — AppID/Secret OAuth，草稿发布
- **[SegmentFault](segmentfault.md)** — Cookie 认证，技术专栏
- **[X/Twitter](twitter.md)** — OAuth 1.0a，tweet/thread
- **[小红书](xiaohongshu.md)** — Cookie 认证，笔记发布
- **[Medium](medium.md)** — API key，国际博客
