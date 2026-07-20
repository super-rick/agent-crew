# AgentCrew MCN 🤖

<div align="center">

**Your AI marketing team. Works 24/7. Never asks for a raise.**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)]()
[![PyPI version](https://img.shields.io/badge/pypi-agentcrew--mcn-blue)](https://pypi.org/project/agentcrew-mcn/)
[![CI](https://github.com/super-rick/agentcrew-mcn/actions/workflows/ci.yml/badge.svg)](https://github.com/super-rick/agentcrew-mcn/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-392%20passed-brightgreen)]()
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue)](https://super-rick.github.io/agentcrew-mcn/)
[![Coverage](https://img.shields.io/badge/coverage-85%25-green)]()

</div>

> 📖 [中文文档](README_CN.md) | English

---

## What is AgentCrew?

AgentCrew MCN is an open-source multi-agent content marketing automation tool. A team of AI "employees" handles the entire pipeline — from content creation to cross-platform distribution.

- **Writer Agent** — Copywriter: generates technical articles, social posts, and threads
- **Reviewer Agent** — QA: pre-publish content safety and quality review
- **Publisher Agent** — Operations: publishes to Juejin, Zhihu, Dev.to, and more
- **Analyst Agent** — Data Analyst: tracks performance and smart scheduling

## Features

- 🧠 **4 AI Agents** — Writer, Reviewer, Publisher, Analyst — each operates independently
- 🔧 **Skills + Tools System** — Atomic operations composed into high-level capabilities (v0.4: LLM-driven)
- 📚 **RAG Knowledge Base** — Retrieval-augmented generation from historical content
- 🌍 **Cross-Platform Publishing** — Juejin, Zhihu, Dev.to with platform-specific style adaptation
- 🔌 **Multi-Provider LLM** — DeepSeek, OpenAI, Anthropic, Ollama — switch with one config field
- 🖼️ **Image Generation** — DALL-E 3 cover images for articles
- ⏰ **Smart Scheduling** — Analyst predicts best publish times with random jitter anti-detection
- 📊 **Dashboard + Growth Tracking** — Web UI for analytics + GROWTH.md for metrics
- 🐳 **Docker** — One-command deployment with docker-compose
- 🔁 **Dogfooding** — The project promotes itself

## Quick Start

### Option 1: pip install (recommended)

```bash
# 1. Install
pip install agentcrew-mcn

# 2. Initialize config
agentcrew-mcn init

# 3. Edit .env with your API keys
#    DEEPSEEK_API_KEY=sk-...

# 4. Start using
agentcrew-mcn write generate --topic "Python async programming" --style technical
agentcrew-mcn publish post --file article.md --platform juejin --dry-run
```

> 💡 `agent-crew` is also available as an alias for `agentcrew-mcn`.

### Option 2: From source

```bash
# 1. Clone
git clone https://github.com/super-rick/agentcrew-mcn.git
cd agentcrew-mcn

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize
python -m cli.main init

# 4. Edit .env with your API keys
```

### Configuration

`agentcrew-mcn init` creates a config template. Key settings:

```yaml
# config.yaml
llm:
  api_key: ${DEEPSEEK_API_KEY}  # Reads from .env
  model: deepseek-chat

platforms:
  juejin:
    cookie: ${JUEJIN_COOKIE}    # Export cookie from browser
  devto:
    api_key: ${DEVTO_API_KEY}   # https://dev.to/settings/extensions
```

### Usage

```bash
# Generate a technical article
agentcrew-mcn write generate --topic "Python async programming" --style technical

# Preview mode (no LLM call, inspect parameters)
agentcrew-mcn write generate --topic "Python async" --dry-run

# Publish to Juejin
agentcrew-mcn publish post --file article.md --platform juejin

# Scheduled publishing (every 6 hours)
agentcrew-mcn schedule start --topic-file topics.txt --platform juejin --interval 6

# RAG knowledge base
agentcrew-mcn rag ingest --file article.md --source "my_blog"
agentcrew-mcn rag search --query "AI Agent architecture"
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Orchestrator                       │
│           Task dispatch / Scheduler / Config          │
└──┬──────────┬──────────────┬────────────────────────┘
   │          │              │
┌──▼──────┐ ┌▼────────┐ ┌──▼────────┐
│ Writer  │ │Publisher│ │  Analyst  │
│ Agent   │ │Agent    │ │  Agent    │
│         │ │         │ │           │
│ Skills: │ │ Skills: │ │ Skills:   │
│ trending│ │ schedule│ │ report    │
│ tech    │ │ multi   │ │ recommend │
│ thread  │ │ batch   │ │           │
│         │ │         │ │           │
│ Tools:  │ │ Tools:  │ │ Tools:    │
│ search  │ │ devto   │ │ analytics │
│ rag     │ │ juejin  │ │ compare   │
│ compose │ │ zhihu   │ │ report    │
└─────────┘ └─────────┘ └───────────┘
```

## Dashboard

AgentCrew includes a **Streamlit Dashboard** for monitoring your AI marketing team.

![Dashboard Overview](screenshots/dashboard-overview.png)

<details>
<summary>More Dashboard Pages</summary>

| Publish Analysis | AI Analysis |
|:-:|:-:|
| ![Publishing](screenshots/dashboard-publishing.png) | ![Analytics](screenshots/dashboard-analytics.png) |

</details>

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| CLI | Click + Rich |
| LLM | DeepSeek API (OpenAI-compatible) |
| Vector DB | ChromaDB |
| Automation | Playwright |
| Dashboard | Streamlit + Plotly |

## Roadmap

See [ROADMAP.md](ROADMAP.md) for details.

- **v0.1** ✅ Writer + Publisher + CLI + Juejin/Zhihu + Dashboard
- **v0.2** ✅ Dev.to adapter + RAG + MCP + Bilingual README
- **v0.3** ✅ Reviewer Agent + Retry + Persistence + Docker (332 tests)
- **v0.4** ✅ LLM-driven Skills + Multi-provider + Image gen + Smart scheduling
- **v0.5** ✅ 6 new platforms (CSDN/WeChat/SegmentFault/X/Xiaohongshu/Medium)
- **v1.0** 🔮 Web API + Plugins + Community

## License

MIT
