# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AgentCrew MCN** — AI MCN 自动推广工具。多 Agent 架构的开源内容营销自动化工具，自动完成从内容生成到跨平台分发的全流程。

核心叙事：项目自己推广自己（Dogfooding / Meta 闭环）。

路线图详见 [ROADMAP.md](ROADMAP.md)（中文: [ROADMAP_ZH.md](ROADMAP_ZH.md)）。

## Documentation Convention

- **All documentation defaults to English.** Chinese versions use `_ZH` suffix or `zh/` subdirectory.
- ROADMAP: `ROADMAP.md` (EN) + `ROADMAP_ZH.md` (CN)
- README: `README.md` (EN) + `README_CN.md` (CN)
- Docs site: `docs/` (EN) + `docs/zh/` (CN), with i18n plugin for language switching
- CLAUDE.md: mixed (technical terms in English, descriptions in Chinese)

## Commands

```bash
# 安装依赖（需要代理时先 export HTTP_PROXY）
pip install -r requirements.txt

# 写作
python -m cli.main write generate --topic "主题" --style technical
python -m cli.main write generate --topic "主题" --platform juejin --rag

# 发布
python -m cli.main publish post --text "内容" --platform juejin --dry-run
python -m cli.main publish post --file article.md --platform juejin --platform zhihu
python -m cli.main publish status
python -m cli.main publish history

# 调度
python -m cli.main schedule start --topic-file topics.txt --platform juejin --interval 6
python -m cli.main schedule stop
python -m cli.main schedule status

# 知识库
python -m cli.main rag ingest --file article.md --source blog
python -m cli.main rag search --query "Python 异步编程"
python -m cli.main rag stats

# Dashboard
streamlit run dashboard/app.py

# MCP
python -m cli.main mcp serve
python -m cli.main mcp serve --transport sse --port 8090
python -m cli.main mcp list-tools
python -m cli.main mcp status

# 测试
python -m pytest tests/ -v
python -m pytest tests/test_agents/test_writer.py -v
python -m pytest tests/test_agents/ -v

# 代码格式化
make fmt
make lint
```

## Architecture

### 核心概念：AI 员工（Agent）

| Agent | 职责 | 已实现 |
|-------|------|--------|
| Writer Agent | 内容生成（调用 LLM + RAG + Skills） | ✅ v0.1 |
| Publisher Agent | 跨平台内容发布（注册多个适配器） | ✅ v0.1 |
| Analyst Agent | 效果分析、策略优化 | ✅ v0.2 |

每个 Agent 继承 `BaseAgent`（`agents/base.py`），拥有独立的 Tool 和 Skill 注册表。

### Skills + Tools 抽象层

```
Tool = 原子操作（web_search, fetch_url_content, get_current_time）
Skill = Tool 的有序编排（trending_writing, technical_article, thread_writing）
```

- **Tool** (`agents/tools.py`): `Tool` 类 + `ToolRegistry`，每个 Tool 可转为 OpenAI Function Calling 格式
- **Skill** (`agents/skills.py`): `Skill` 抽象类 + `SkillRegistry`，`execute(registry, params)` 编排多个 Tool
- Agent 初始化时自动注册 BUILTIN_TOOLS 和 BUILTIN_SKILLS

### Platform 适配器模式

```
BasePlatformAdapter (platforms/base.py)
├── JuejinAdapter (platforms/juejin.py) — Cookie 认证，API 发文章/沸点
├── ZhihuAdapter (platforms/zhihu.py) — Playwright 浏览器自动化
└── DevToAdapter (platforms/devto.py) — Forem API
```

每个适配器实现 `authenticate()` + `post(content: ContentPost) → PostResult`。

### 数据流

```
CLI → Orchestrator.execute_pipeline()
  ├── WriterAgent.execute() — RAG 检索 → Skill 编排 → LLM 生成 → 平台格式化
  │   ├── _enrich_context(topic)   # RAG 检索 + Web 搜索
  │   ├── _build_messages()        # 组装 system + context + user prompt
  │   └── format_for_platform()    # juejin / zhihu / devto 格式适配
  │
  └── PublisherAgent.execute() — 内容验证 → 各平台适配器 → 记录结果
```

### RAG 模块

```
rag/embedder.py     — OpenAIEmbedder（OpenAI 兼容）+ create_embedder 工厂（多协议可扩展）
rag/knowledge_base.py — ChromaDB 封装（add_documents/search/get_stats）
rag/retriever.py    — 检索管道（retrieve_for_writing/format_context）
```

> **注意**: 硅基流动 BGE 模型限制 ~512 tokens/chunk。批量嵌入时需分批（3-5 chunks/次），
> 避免 payload 过大导致 OOM 或 API 400 错误。CHUNK_SIZE 建议 500-800 字符。

### MCP 模块

```
crew_mcp/adapter.py  — AgentCrew Tool ↔ MCP tool 格式双向转换
crew_mcp/server.py   — MCPServer，将 AgentCrew 工具暴露为 MCP Server（stdio/SSE）
crew_mcp/client.py   — MCPClientManager，连接外部 MCP Server 发现并注入工具
crew_mcp/config.py   — MCP 配置 dataclass + YAML 解析
crew_mcp/cli.py      — CLI：mcp serve / list-tools / status
```

### 关键目录

```
agents/       Agent 实现 + Tool/Skill 系统
crew_mcp/     MCP 协议（Server + Client + CLI）
orchestrator/ 任务编排引擎 + 调度器（带随机抖动反检测）
platforms/    各平台适配器（可插拔）
rag/          RAG 知识库
llm/          LLM Client（OpenAI 兼容，对接 DeepSeek）
cli/          Click CLI 命令
dashboard/    Streamlit Web 面板（4 页面：总览/发布分析/AI 分析/系统状态）
data/         运行时数据（chroma 向量库 / 日志）
```

## Key Decisions

- **语言**: Python（AI 生态最佳）
- **LLM**: DeepSeek API（OpenAI 兼容格式）
- **向量库**: ChromaDB（本地轻量）
- **CLI**: Click + Rich
- **配置**: YAML with `${ENV_VAR}` 变量替换
- **Python 版本**: 3.10+（代码使用 `X | None` 联合类型语法；Python 3.9 需 `from __future__ import annotations`）
- **MCP**: crew_mcp 模块（MCP Server + Client），基于官方 mcp SDK
- **开发顺序**: CLI 优先，Dashboard 最后

## Platform Delays

- **掘金**: Cookie 认证（`authenticate()` 时验证）。API 发文章需 title，沸点无需
- **知乎**: Playwright 浏览器自动化，Cookie 持久化，随机延迟反检测（需要在有 GUI 的环境首次配置 Cookie）
- **Dev.to**: Forem API，API key 认证

## Testing

- 单元测试用 `unittest.mock` 完全隔离 LLM 和网络调用
- `conftest.py` 提供 `mock_llm_client` 和 `mock_web_search`（autouse）fixtures
- 集成测试在 `tests/test_integration/`，测试 Orchestrator 编排完整 pipeline
- 平台适配器测试需 mock 外部 API

## CI/CD & Release

- **PyPI 发布已自动化**：push tag `v*` → GitHub Actions `publish.yml` 自动 build + twine upload
- **不需要手动 `twine upload`**。打 tag 后等 CI 完成即可
- 版本号在 `pyproject.toml` 中修改，commit 后打 tag

## 当前进度 / Current Progress

> **每次完成阶段性工作后更新此段。** 新 session 从这里开始，无需重新调查。

### 已完成

| 模块 | 状态 | 说明 |
|------|------|------|
| Writer Agent | ✅ v0.1 | 内容生成（LLM + RAG + Skills），含动态 Skill 编排 |
| Reviewer Agent | ✅ v0.4 | 发布前内容审核（敏感词/平台规范/质量评分） |
| Publisher Agent | ✅ v0.1 | 跨平台发布，适配器模式，9 个平台适配器 |
| Analyst Agent | ✅ v0.2 | 效果分析 + 智能排期 |
| CLI 命令 | ✅ | write / publish / schedule / rag / analyst / mcp / init / doctor |
| Dashboard | ✅ v0.2 | Streamlit：总览/发布分析/AI 分析/系统状态 + 增长指标 |
| LLM 多 Provider | ✅ v0.4 | DeepSeek / OpenAI / Anthropic / Ollama + 异步支持 |
| 图片生成 | ✅ v0.4 | DALL-E 3 封面图生成 |
| RAG 模块 | ✅ v0.4 | OpenAIEmbedder + local ONNX fallback + ChromaDB |
| MCP 协议 | ✅ v0.3 | MCP Server + Client，crew_mcp 模块 |
| 重试机制 | ✅ v0.3 | 指数退避 + jitter |
| 持久化调度 | ✅ v0.3 | JSON 存储 + cron 表达式 + schedule resume + --once/--timeout |
| Docker 部署 | ✅ v0.3 | Dockerfile + docker-compose.yml |
| CI/CD | ✅ | GitHub Actions: test (3.10/3.11/3.12) + lint + types + PyPI publish on tag |
| 平台适配器 (9个) | ✅ v0.5 | 掘金/知乎/Dev.to/CSDN/微信/SegmentFault/X(Twitter)/小红书/Medium |
| 文档站 | ✅ v0.5 | MkDocs + 中英双语 (docs/ + docs/zh/) |
| 测试套件 | ✅ | 392 passed, 0 failed |
| Dogfooding | ✅ | 掘金文章已发布：juejin.cn/post/7663435750386303027 |
| Bug 修复 | ✅ 2026-07-21 | #64-#71：空 topic 校验、RAG 状态、dry-run 历史污染、调度器增强、embedding 本地 fallback |

### 待开发（详见 ROADMAP.md）

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 📣 Product Hunt / HN 发布 | 🟡 中 | v0.5 增长 — 正式对外发布 |
| 🏗️ Web API | 🟡 中 | v1.0 — FastAPI + WebSocket + JWT |
| 🧩 插件市场 | 🟢 低 | v1.0 — PyPI 标签 agentcrew-skill / agentcrew-platform |
| 💰 商业化 | 🟢 低 | v2.0 — SaaS + 付费计划 + 企业特性 |

### 已知问题 / Known Issues

| 问题 | 说明 | 缓解 |
|------|------|------|
| RAG 批量嵌入 OOM | 硅基流动 BGE 大批量 chunks 嵌入会超时 | 分批 3-5 chunks，或用 `local` provider |
| Dev.to API key | .env 中 DEVTO_API_KEY 认证失败 | 不阻塞，其他 8 个平台正常 |

### 下一步行动计划（2026-07-21 更新）

> **v0.3～v0.5 核心功能全部完成。当前阶段：v0.5 打磨增长 → v1.0 平台化。**

- 📣 **v0.5 增长**: Product Hunt 发布、HN Show HN、文档站完善
- 🏗️ **v1.0 平台化**: Web API + 用户系统 + 插件市场
- 💰 **v2.0 商业化**: SaaS + 付费计划 + 企业特性
