# Changelog

All notable changes to AgentCrew MCN will be documented in this file.

---

## [0.2.0] — 2026-07-17

### Added
- **Dev.to 适配器** — Forem API 集成，API key 认证，支持 Markdown 文章发布 (`platforms/devto.py`)
- **Bilingual README** — `README.md` (English) + `README_CN.md` (中文)，修复命令格式错误
- **ROADMAP.md** — v0.1 ~ v1.0 详细路线图
- Dev.to 认证端点使用 `/articles/me`（兼容新版 API key 权限策略）

### Fixed
- **知乎 Markdown 格式修复** — 使用剪贴板粘贴触发知乎的"导入 Markdown"弹窗，点击确认解析后再发布。修复前 Markdown 原文直接显示为纯文本
- Code review 发现的 7 个问题（资源泄漏、空安全、假测试、CLAUDE.md 过期引用等）
- Dev.to 认证失败（`/users/me` 对新 API key 返回 401）

### Changed
- Twitter/X 适配器 → Dev.to 适配器（无 Twitter 账号，Dev.to API 更简单且面向全球开发者）
- 架构图中 twitter → devto
- CLAUDE.md 中所有 Twitter 引用更新为 Dev.to

---

## [0.1.2] — 2026-07-16

### Added
- PyPI 发布 `agentcrew-mcn` 包
- `publish auth` 命令用于交互式知乎登录 (Playwright storage_state)
- `--project-info` 用于 `write generate` 和 `schedule start`
- 从 Markdown 文件自动提取标题 (`publish post --file`)

### Fixed
- 知乎代码块渲染（inline styles、缩进保留、white-space:pre）
- Playwright storage_state 知乎认证持久化
- CLI 命令引用中缺失的空格

### Changed
- 项目重命名为 agentcrew-mcn（从 agent-crew）

---

## [0.1.0] — 2026-07-15

### Added
- **Writer Agent** — AI 内容生成（LLM + RAG + Skills）
- **Publisher Agent** — 跨平台内容分发（适配器模式）
- **Analyst Agent** — 效果分析、推荐、排名
- **掘金适配器** — Cookie 认证，API 发布文章/沸点
- **知乎适配器** — Playwright 浏览器自动化，Cookie 持久化
- **RAG 知识库** — ChromaDB + DeepSeek Embedding
- **CLI** — Click + Rich（write / publish / schedule / rag 四组命令）
- **Dashboard** — Streamlit Web 面板（4 页面）
- **调度器** — 带随机抖动反检测的定时发布
- Meta 闭环 Dogfooding 策略

---

[0.2.0]: https://github.com/super-rick/agentcrew-mcn/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/super-rick/agentcrew-mcn/compare/v0.1.0...v0.1.2
[0.1.0]: https://github.com/super-rick/agentcrew-mcn/releases/tag/v0.1.0
