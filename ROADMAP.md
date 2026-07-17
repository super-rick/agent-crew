# AgentCrew MCN Roadmap

## v0.1 — Foundation ✅

Released July 2026.

- [x] **Writer Agent** — AI content generation (LLM + RAG + Skills)
- [x] **Publisher Agent** — Cross-platform distribution with pluggable adapters
- [x] **Analyst Agent** — Performance analysis, recommendations, ranking
- [x] **Juejin Adapter** — Cookie-based API posting (articles + pins)
- [x] **Zhihu Adapter** — Playwright browser automation with anti-detection
- [x] **RAG Module** — ChromaDB + SiliconFlow BGE embedding
- [x] **CLI** — Click + Rich: `write`, `publish`, `schedule`, `rag`, `analyst`
- [x] **Dashboard** — Streamlit web panel (4 pages: Overview, Posts, Analysis, Status)
- [x] **Scheduler** — Time-based publishing with random jitter
- [x] **Test Suite** — 88 unit + integration tests, fully mocked external APIs
- [x] **PyPI Release** — `agentcrew-mcn` package published

## v0.2 — Polish & Expand 📝

_Current. Targeting Q3 2026._

- [x] ~~X/Twitter adapter~~ → Redirected to Dev.to (no Twitter account)
- [ ] **Dev.to Adapter** — Forem API integration for global developer audience
- [ ] **Zhihu Markdown Fix** — Clipboard paste + "import Markdown" dialog handling
- [ ] **Bilingual README** — README.md (EN) + README_CN.md (CN)
- [ ] **Dogfooding Round 1** — Run full pipeline: generate → publish real articles
- [ ] **CLI UX Improvements** — Better error messages, progress indicators
- [ ] **More Platform Options** — Evaluate CSDN, SegmentFault, Medium

## v0.3 — Ecosystem 🔜

_Planning. Targeting Q4 2026._

- [ ] **Skill Store** — Shareable writing skills, community contributions
- [ ] **More Platforms** — CSDN, SegmentFault, Weibo based on community demand
- [ ] **A/B Testing** — Compare post performance across platforms and styles
- [ ] **Content Templates** — Pre-built templates for common article types
- [ ] **Multi-LLM Support** — Claude, GPT, Gemini as alternative backends
- [ ] **Analytics v2** — Engagement tracking, trend detection, keyword optimization
- [ ] **Config Wizard** — Interactive `init` command with guided setup

## v1.0 — MCP & Community 🔮

_Long-term. Targeting 2027._

- [ ] **MCP Protocol** — Model Context Protocol for tool access
  - MCP Server: expose AgentCrew tools to other AI apps
  - MCP Client: connect external tools into AgentCrew agents
- [ ] **Plugin System** — Community-built platform adapters and skills
- [ ] **Web UI** — Beyond dashboard: full web-based content management
- [ ] **Multi-User Support** — Team collaboration on content pipelines
- [ ] **Content Calendar** — Visual planning with drag-and-drop scheduling
- [ ] **API Server** — REST API for third-party integration

## Never / Maybe

- Paid features / proprietary licensing — project stays MIT
- Video content generation — out of scope (text-focused)
- Social media engagement bot (auto-reply, auto-follow) — ethical boundary
