# AgentCrew MCN Roadmap

> Current: **v0.5.1** | Updated: 2026-07-20 | [中文版](ROADMAP_ZH.md)

## Overview

```
               v0.3              v0.4              v0.5           v1.0              v2.0
Engineering ── Reliability ──── Intelligence ─── Platforms ─── Platformization ── Commercial
Growth      ── Repo Health ─── Dogfooding    ─── Launch    ─── Community ─────── SaaS
```

## Completed

| Phase | Highlights | Tests | Date |
|-------|-----------|-------|------|
| **v0.3** Reliability | Reviewer Agent, Retry, Persistent Scheduler, Docker, Growth infra | 268 | Jul 19 |
| **v0.4** Intelligence | LLM-driven Skills, Multi-provider LLM, DALL-E 3, Smart Scheduling, Cross-platform | 317 | Jul 19 |
| **v0.5** Platforms | CSDN, WeChat, SegmentFault, X/Twitter, Xiaohongshu, Medium (6 new) | 392 | Jul 20 |
| **Tech Debt** | Type annotations (mypy 0), 86% coverage, Async, JSON logging, Docs | — | Jul 20 |

**Stats:** 4 Agents · 9 Platforms · 5 LLM Providers · 392 tests · 54 PRs

## Now: v1.0 — Platformization

- **Web API** — FastAPI + WebSocket + JWT
- **Dashboard Upgrade** — Content calendar, AI chat, mobile
- **User System** — PostgreSQL + multi-user + RBAC
- **Plugin Marketplace** — PyPI tags `agentcrew-skill` / `agentcrew-platform`

### Growth: Community

- Community plugin marketplace
- Contributor recognition
- GitHub Sponsors
- Conference talks (PyCon/AI)

## Future: v2.0 — Commercial

- SaaS deployment (K8s Helm)
- Paid plans (Free / Pro / Team / Enterprise)
- Advanced analytics (ROI, A/B testing)
- Enterprise features (SSO, audit, white-label)

---

## Key Metrics

| Metric | Now | v1.0 Goal |
|--------|-----|-----------|
| GitHub Stars | 1 | 2,000 |
| PyPI Downloads | - | 1,000/mo |
| Contributors | 1 | 20+ |

---

📖 [Documentation](https://super-rick.github.io/agentcrew-mcn/) · [Wiki](https://github.com/super-rick/agentcrew-mcn/wiki)
