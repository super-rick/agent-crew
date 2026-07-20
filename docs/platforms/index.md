# 平台配置

AgentCrew 支持 9 个内容平台。每个平台需要不同的认证方式。

## 平台总览

| 平台 | 认证 | 配置字段 | 优先级 |
|------|------|----------|--------|
| 掘金 | Cookie | `JUEJIN_COOKIE` | 已支持 |
| 知乎 | Cookie (Playwright) | 浏览器自动化 | 已支持 |
| Dev.to | API Key | `DEVTO_API_KEY` | 已支持 |
| CSDN | Cookie | `CSDN_COOKIE` | v0.5 |
| 微信公众号 | AppID + Secret | `WECHAT_APP_ID/SECRET` | v0.5 |
| SegmentFault | Cookie | `SEGMENTFAULT_COOKIE` | v0.5 |
| X/Twitter | OAuth 1.0a | API Key + Secret + Token | v0.5 |
| 小红书 | Cookie | `XIAOHONGSHU_COOKIE` | v0.5 |
| Medium | API Key | `MEDIUM_API_KEY` | v0.5 |

## 通用认证流程

### Cookie 认证（掘金/CSDN/SegmentFault/小红书）

1. 浏览器登录目标平台
2. F12 → Application → Cookies
3. 复制所有 Cookie 字符串
4. 填入 `.env` 对应字段

### API Key 认证（Dev.to/Medium）

1. 平台设置页面生成 API Key
2. 填入 `.env`

### OAuth 认证（微信/X）

1. 开发者后台获取 AppID/Secret
2. 填入 `.env`

### Playwright 认证（知乎）

首次需要 GUI 环境手动登录，Cookie 自动持久化。
