# AgentCrew MCN 未来路线图

> 当前版本: **v0.5.1** | 更新: 2026-07-20 | [English](ROADMAP.md)

## 总览

```
               v0.3              v0.4              v0.5           v1.0              v2.0
🔧 工程  ── 可靠性加固 ──── 智能升级 ──── 平台扩展 ──── 平台化 ──────── 商业化
📈 增长  ── 仓库健康   ──── Dogfooding ──── 对外发布 ──── 社区生态 ──── SaaS
```

## 已完成

| Phase | 核心交付 | Tests |
|-------|----------|-------|
| **v0.3** 可靠性 | Reviewer Agent · 重试机制 · 持久化调度 · Docker · GitHub Topics/Badges | 268 |
| **v0.4** 智能 | LLM-driven Skills · 多Provider · DALL-E 3 · 智能排期 · 跨平台适配 | 317 |
| **v0.5** 平台 | CSDN · 微信 · SegmentFault · X/Twitter · 小红书 · Medium (6个新平台) | 392 |
| **技术债务** | mypy 0 errors · 86% 覆盖率 · Async · JSON 日志 · 双语文档站 | — |

**当前**: 4 Agents · 9 平台 · 5 Providers · 392 tests · 54 PRs

---

## v1.0 — 平台化

> **目标**: 从 CLI 工具升级为 Web 平台。

- **Web API** — FastAPI + WebSocket + JWT 认证
- **Dashboard 升级** — 内容日历、AI 对话、移动端适配
- **用户系统** — PostgreSQL + 多用户隔离 + RBAC
- **插件市场** — PyPI 标签 `agentcrew-skill` / `agentcrew-platform`

**📈 增长**: 社区插件市场 · 贡献者认可 · GitHub Sponsors · 会议演讲

## v2.0 — 商业化

- **SaaS** — K8s Helm Chart · 多租户
- **付费** — Free / Pro (¥99/月) / Team (¥499/月)
- **企业** — SSO · 审计 · 私有部署 · 白标

---

## 关键指标

| 指标 | 当前 | v1.0 目标 |
|------|------|-----------|
| GitHub Stars | 1 | 2,000 |
| PyPI 下载 | - | 1,000/月 |
| 贡献者 | 1 | 20+ |

## 待办

- [ ] 性能优化（LLM 缓存、RAG 加速）
- [ ] 安全审计（Cookie 加密、Key 轮换）
- [ ] Product Hunt 发布
- [ ] HN Show HN

---

📖 [文档站](https://super-rick.github.io/agentcrew-mcn/) · [Wiki](https://github.com/super-rick/agentcrew-mcn/wiki)
