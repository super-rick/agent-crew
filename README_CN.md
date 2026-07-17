# AgentCrew MCN 🤖

<div align="center">

**你的 AI 营销团队，24 小时在线工作，不领工资。**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)]()
[![PyPI version](https://img.shields.io/badge/pypi-agentcrew--mcn-blue)](https://pypi.org/project/agentcrew-mcn/)
[![Tests](https://img.shields.io/badge/tests-88%20passed-brightgreen)]()

</div>

> 📖 [English README](README.md) | 中文文档

---

## 什么是 AgentCrew？

AgentCrew MCN 是一个开源的多 Agent 内容营销自动化工具。它由一组 AI"员工"组成，自动完成从内容生成到跨平台分发的全流程。

- **Writer Agent** — 文案员工：生成技术文章、帖子、Thread
- **Publisher Agent** — 运营员工：发布到掘金、知乎、Dev.to
- **Analyst Agent** — 数据分析员工：追踪效果、优化策略

## 核心特性

- 🧠 **多 Agent 架构** — 每个"员工"独立部署，可插拔
- 🔧 **Skills + Tools 系统** — 原子化操作 + 高级能力编排
- 📚 **RAG 知识库** — 基于历史内容和竞品情报的增强生成
- 🎯 **跨平台发布** — 支持掘金、知乎、Dev.to 等平台
- ⏰ **智能调度** — 带随机抖动的定时发布，避免平台检测
- 🔮 **MCP 预留** — 架构预留 MCP 协议接口（v2 路线图）
- 📊 **Dashboard** — Web 面板查看发布数据和 Agent 状态
- 🔁 **自推广 Meta 闭环** — 项目自己推广自己

## 快速开始

### 方式一：pip 安装（推荐）

```bash
# 1. 安装
pip install agentcrew-mcn

# 2. 初始化配置
agentcrew-mcn init

# 3. 编辑 .env，填入你的 API Key
#    DEEPSEEK_API_KEY=sk-...

# 4. 开始使用
agentcrew-mcn write generate --topic "Python 异步编程" --style technical
agentcrew-mcn publish post --file article.md --platform juejin --dry-run
```

> 💡 也可使用 `agent-crew` 命令，与 `agentcrew-mcn` 完全等价。

### 方式二：源码安装

```bash
# 1. 克隆项目
git clone https://github.com/super-rick/agentcrew-mcn.git
cd agentcrew-mcn

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化配置
python -m cli.main init

# 4. 编辑 .env，填入 API Key
```

### 配置

`agentcrew-mcn init` 会自动创建配置文件模板。主要配置项：

```yaml
# config.yaml 核心配置
llm:
  api_key: ${DEEPSEEK_API_KEY}  # 从 .env 读取
  model: deepseek-chat

platforms:
  juejin:
    cookie: ${JUEJIN_COOKIE}    # 浏览器登录后导出 Cookie
```

### 使用

```bash
# 生成一篇技术文章
agentcrew-mcn write generate --topic "Python 异步编程" --style technical

# 预览模式（不调用 LLM，查看参数）
agentcrew-mcn write generate --topic "Python 异步编程" --dry-run

# 发布到掘金
agentcrew-mcn publish post --file article.md --platform juejin

# 启动定时发布（每 6 小时）
agentcrew-mcn schedule start --topic-file topics.txt --platform juejin --interval 6

# 管理 RAG 知识库
agentcrew-mcn rag ingest --file article.md --source "my_blog"
agentcrew-mcn rag search --query "AI Agent 架构"
```

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                   Orchestrator                       │
│              任务分派 / 调度引擎 / 配置管理              │
└──┬──────────┬──────────────┬────────────────────────┘
   │          │              │
┌──▼──────┐ ┌▼────────┐ ┌──▼────────┐
│ Writer  │ │Publisher│ │  Analyst  │
│ Agent   │ │Agent    │ │  Agent    │
│         │ │         │ │           │
│ Skills: │ │ Skills: │ │ Skills:   │
│ 追热点   │ │ 定时分发 │ │ 效果分析   │
│ 技术文章 │ │ 多平台  │ │ 趋势报告   │
│ Thread   │ │ 批量    │ │           │
│         │ │         │ │           │
│ Tools:  │ │ Tools:  │ │ Tools:    │
│ search  │ │ devto   │ │ analytics │
│ rag     │ │ juejin  │ │ compare   │
│ compose │ │ zhihu   │ │ report    │
└─────────┘ └─────────┘ └───────────┘
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| CLI | Click + Rich |
| LLM | DeepSeek API (OpenAI 兼容) |
| 向量库 | ChromaDB |
| 自动化 | Playwright |
| Dashboard | Streamlit + Plotly |

## 路线图

详见 [ROADMAP.md](ROADMAP.md)。

- **v0.1** ✅ Writer Agent + Publisher Agent + CLI + 掘金/知乎 + Dashboard + Analyst Agent
- **v0.2** 📝 Dev.to 适配器 + 知乎 MD 优化 + README 中英双语
- **v0.3** 🔜 Skill Store + 更多平台 + 发布效果对比
- **v1.0** 🔮 MCP 协议 + 社区插件

## License

MIT
