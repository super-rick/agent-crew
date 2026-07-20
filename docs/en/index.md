# 🤖 AgentCrew MCN

**Your AI marketing team. Works 24/7. Never asks for a raise.**

AgentCrew MCN is an open-source multi-agent content marketing automation tool. 4 AI employees handle content creation → review → publishing → analytics.

## Quick Start

```bash
pip install agentcrew-mcn
agentcrew-mcn init
# Edit .env with DEEPSEEK_API_KEY
agentcrew-mcn write generate -t "Python async programming" -p devto
```

## Core Features

- 🧠 **4 AI Agents** — Writer, Reviewer, Publisher, Analyst
- 🌍 **9 Platforms** — Juejin, Zhihu, Dev.to, CSDN, WeChat, SegmentFault, X/Twitter, Xiaohongshu, Medium
- 🔌 **5 LLM Providers** — DeepSeek, OpenAI, Anthropic, Ollama, OpenAI-compatible
- 📚 **RAG Knowledge Base** — ChromaDB powered
- 🖼️ **AI Cover Images** — DALL-E 3
- ⏰ **Smart Scheduling** — Analyst predicts best publish times
- 🐳 **Docker** — `docker compose up dashboard`

## Architecture

```
Orchestrator → Writer → Reviewer → Publisher
                        ↓
                      Analyst
```

## Next

- [Installation](../installation.md)
- [Writing Content](../writing.md)
- [Platform Setup](../platforms/index.md)
