# 🤖 AgentCrew MCN

**Your AI marketing team. Works 24/7. Never asks for a raise.**

AgentCrew MCN is an open-source multi-agent content marketing automation tool. 4 AI employees handle the full pipeline: content creation → safety review → cross-platform publishing → performance analytics.

## Key Features

- 🧠 **4 AI Agents** — Writer, Reviewer, Publisher, Analyst
- 🌍 **9 Platforms** — Juejin, Zhihu, Dev.to, CSDN, WeChat, SegmentFault, X/Twitter, Xiaohongshu, Medium
- 🔌 **5 LLM Providers** — DeepSeek, OpenAI, Anthropic, Ollama, OpenAI-compatible
- 📚 **RAG Knowledge Base** — ChromaDB vector search
- 🖼️ **AI Cover Images** — DALL-E 3 integration
- ⏰ **Smart Scheduling** — Analyst predicts best publish times
- 🐳 **Docker** — `docker compose up dashboard`
- 📊 **Dashboard** — Streamlit web UI

## 30-Second Quick Start

```bash
pip install agentcrew-mcn
agentcrew-mcn init
# Edit .env with DEEPSEEK_API_KEY
agentcrew-mcn write generate -t "Python async programming" -p devto
```

## Architecture

```
Orchestrator
├── Writer Agent    → Content generation (LLM + RAG + Skills)
├── Reviewer Agent  → Content safety & quality check
├── Publisher Agent → Cross-platform distribution
└── Analyst Agent   → Performance analytics & smart scheduling
```

## Next Steps

- [Installation](installation.md) — pip, source, Docker setup
- [Writing Content](writing.md) — Writer Agent guide
- [Platform Setup](platforms/index.md) — Configure 9 platforms
