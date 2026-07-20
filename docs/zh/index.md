[:us: English](/){ .md-button }

# 🤖 AgentCrew MCN

**你的 AI 营销团队，24 小时在线工作，不领工资。**

AgentCrew MCN 是一个开源的多 Agent 内容营销自动化工具。4 个 AI 员工（Writer, Reviewer, Publisher, Analyst）自动完成从内容生成到跨平台分发的全流程。

## 核心特性

- 🧠 **4 个 AI Agent** — 写作、审核、发布、分析，各司其职
- 🌍 **9 个内容平台** — 掘金、知乎、Dev.to、CSDN、微信、SegmentFault、X/Twitter、小红书、Medium
- 🔌 **5 个 LLM Provider** — DeepSeek、OpenAI、Anthropic、Ollama、自定义兼容
- 📚 **RAG 知识库** — ChromaDB 向量检索，历史内容增强生成
- 🖼️ **AI 封面图** — DALL-E 3 自动生成文章封面
- ⏰ **智能排期** — Analyst 分析最佳发布时间，随机抖动反检测
- 🐳 **Docker 部署** — 一键 `docker compose up`
- 📊 **Dashboard** — Streamlit Web 面板监控 AI 营销团队
- 🔁 **Dogfooding** — 项目自己推广自己

## 30 秒快速开始

```bash
# 1. 安装
pip install agentcrew-mcn

# 2. 初始化配置
agentcrew-mcn init

# 3. 编辑 .env，填入 DeepSeek API key

# 4. 生成第一篇文章
agentcrew-mcn write generate -t "Python async programming" -p juejin
```

## 架构

```
┌─────────────────────────────────────────┐
│           Orchestrator                   │
│     任务调度 / 配置管理 / 重试机制        │
└──┬──────────┬──────────┬────────────────┘
   │          │          │
┌──▼──┐  ┌───▼───┐  ┌──▼──────┐  ┌───────┐
│Writer│  │Reviewer│  │Publisher│  │Analyst│
│ 写作 │  │  审核  │  │  发布   │  │ 分析  │
└─────┘  └───────┘  └─────────┘  └───────┘
```

## 下一步

- [安装配置](installation.md) — 详细安装步骤
- [内容创作](writing.md) — Writer Agent 使用指南
- [发布管理](publishing.md) — 多平台发布
