# AgentCrew MCN 未来路线图 (Roadmap)

> 当前版本: **v0.4.0 (Beta)** | 最后更新: 2026-07-19

AgentCrew MCN 是一个多 Agent 架构的开源内容营销自动化工具。已完成核心闭环：Writer → Publisher → Analyst，支持掘金/知乎/Dev.to 三个平台，具备 RAG、MCP 协议、Streamlit Dashboard、定时调度等能力。203 个测试全部通过。

### 双轨路线图 / Dual-Track Roadmap

本路线图采用**工程 + 增长双轨并行**模式。最好的工具没人发现等于不存在——工程决定产品下限，增长决定产品上限。

- **🔧 工程轨道 (Engineering)**: 产品质量、可靠性、智能能力、平台扩展
- **📈 增长轨道 (Growth)**: 可见性、上手体验、社区建设、Dogfooding 内容营销

> 核心叙事：**项目自己推广自己**（Dogfooding / Meta 闭环）。AgentCrew 的推广内容全部由 AgentCrew 自己生成和发布。

---

## 总览

```
                    v0.3                  v0.4                  v0.5                  v1.0                  v2.0
🔧 工程   ── 可靠性加固 ──── 智能升级 ──── 平台扩展 ──── 平台化 ──────── 商业化
📈 增长   ── 仓库健康   ──── Dogfooding规模化 ── Product Hunt ── 社区生态 ──── SaaS增长
```

---

## Phase 1: v0.3 — Reliability & Hardening（可靠性加固）✅ 已完成

> **状态**: ✅ 全部完成（2026-07-19）。268 tests passed。

### 1.1 错误处理与重试机制
- 在 `BaseAgent` 和平台 `adapter.post()` 层加入指数退避重试（3 次）
- `TaskResult` 增加 `retry_count` 字段
- CLI 输出区分"重试中"和"最终失败"

### 1.2 持久化调度器
- 将调度任务持久化到 SQLite（`data/scheduler.db`）
- 新增 `schedule resume` 命令：重启后恢复未完成任务
- 支持 cron 表达式

### 1.3 内容安全审核 — Reviewer Agent
- 新增第 4 个 Agent：发布前自动审核内容
- 审核维度：敏感词、平台规范、内容质量评分
- Pipeline: Writer → Reviewer → Publisher

### 1.4 CI/CD 与工程完善
- `Dockerfile` + `docker-compose.yml`（同时关键解决上手门槛：从 4 步手动配置降到 `docker compose up` 一条命令）
- `.pre-commit-config.yaml`（ruff + black + mypy）
- GitHub Actions: Docker build + 集成测试

### 1.5 已知问题修复
- RAG 批量嵌入 OOM → 自动分批
- Dev.to API key 诊断增强
- CLI spinner + ChromaDB 超时兼容

### 1.6 增长基础：仓库健康与社区启动 (Growth & Community)

> **目标**: 让项目被发现、被信任、被使用。与工程任务并行推进。

#### 1.6.1 仓库可发现性（今天做，10 分钟）

- 添加 15+ GitHub Topics：`ai-agent`, `multi-agent`, `content-marketing`, `deepseek`, `rag`, `chromadb`, `mcp`, `python`, `cli`, `automation`, `juejin`, `zhihu`, `devto`, `streamlit`, `llm`, `openai`
- README 添加 CI status badge + 测试覆盖率 badge（workflows 已存在，只需 badge 链接）
- shields.io 动态 badges：test count、PyPI downloads、stars

#### 1.6.2 上手体验优化

- 🐳 Docker 一键体验：`docker compose up`（从 4 步手动配置降到 1 条命令）
- 🎬 终端 Demo 录制：30s asciicast/GIF 展示 `pip install` → 第一条发布
- 🖼️ README 加入 Dashboard 截图和 Demo GIF（流失 80% 浏览者的关键修复）
- 📋 Demo mode 预配置：mock API key 的体验模式

#### 1.6.3 初始内容与社会证明

- 📝 掘金介绍文章："我写了一个能自己推广自己的 AI 营销团队"（Dogfooding，用项目自身发布）
- 💬 V2EX 发布帖（Create 或 Python 节点）
- 🌐 Reddit r/Python 交叉发帖
- 📋 Issue 模板（bug report + feature request）— 降低贡献门槛

#### 1.6.4 开发者体验基础

- pyproject.toml keywords 扩展（新增 12+ 关键词：`deepseek`, `rag`, `mcp`, `juejin`, `zhihu`, `chromadb`, `cli`, `openai`, `crewai`, `langchain`, `scheduler`）
- GitHub Discussions 开启（社区问答渠道）
- `.pre-commit-config.yaml`（与 1.4 工程任务联动）

---

## Phase 2: v0.4 — Intelligence Upgrade（智能升级）✅ 已完成

> **状态**: ✅ 全部完成（2026-07-19）。317 tests passed。

### 2.1 动态 Skill 编排（LLM-driven）
- Skill 增加 LLM 自主编排模式：根据描述选择 Tool 调用顺序
- 保持向后兼容：`workflow_type: "deterministic" | "llm_driven"`

### 2.2 多模型 Provider 支持
- 重构 `llm/` → 支持 DeepSeek / OpenAI / Anthropic / Ollama
- 为不同 Agent 指定不同模型

### 2.3 图片/多媒体生成
- `ImageGenerationTool` — DALL-E / Stability AI
- Writer Agent 生成封面图

### 2.4 智能排期
- Analyst Agent 分析最佳发布时间
- Scheduler 支持 `smart_schedule` 模式

### 2.5 跨平台内容改编
- 掘金：技术深度 + 代码示例
- 知乎：观点鲜明 + 故事化
- Dev.to：英文版生成

### 2.6 增长：Dogfooding 规模化 (Growth: Dogfooding at Scale)

> **目标**: 用 AgentCrew 自身建立受众。50+ 篇内容矩阵覆盖中英文技术社区。

- 用 AgentCrew 自身发布 50+ 篇文章到掘金/知乎/Dev.to
- 案例文章："AgentCrew 如何建立自己的受众——Dogfooding 案例研究"（高价值内容同时推广工具）
- SEO 关键词研究：README 和文档 targeting "AI content automation", "multi-agent marketing"
- 创建项目 Logo 和视觉品牌
- 公开 `GROWTH.md` 或在 Dashboard 新增增长指标面板
- 开始收集和展示用户案例/Testimonials

---

## Phase 3: v0.5 — Platform Expansion（平台扩展）

> **目标**: 覆盖更多平台，进入国际化。

### 新平台适配器

| 平台 | 优先级 | 认证方式 | 特点 |
|------|--------|----------|------|
| **CSDN** | 🔴 高 | Cookie / API | 国内最大开发者社区 |
| **微信公众平台** | 🔴 高 | API + AppID/Secret | 最大中文内容生态 |
| **SegmentFault (思否)** | 🟡 中 | Cookie | 技术问答+专栏 |
| **X (Twitter)** | 🟡 中 | OAuth 1.0a | 国际化必备 |
| **小红书** | 🟢 低 | App 模拟 | 高价值但难度大 |
| **Medium** | 🟢 低 | API key | 国际化博客 |

- 平台适配器插件化（`importlib.metadata` entry points）
- 社区贡献的第三方适配器 pip installable
- Dashboard 实时平台健康检查

### 增长：Product Hunt & 社区发布 (Growth: Product Hunt & Community Launch)

> **目标**: 多平台成熟时启动正式对外发布，制造增长杠杆。

- 🚀 Product Hunt 发布（叙事："Automated content for N platforms"）
- 📣 Hacker News "Show HN" 帖子
- 📖 官方文档站（MkDocs Material 主题，GitHub Pages）
- 📊 竞品对比页：AgentCrew vs CrewAI vs 手动内容营销
- 🎉 第一位外部贡献者庆祝

---

## Phase 4: v1.0 — Platformization（平台化）

> **目标**: 从 CLI 工具升级为 Web 平台。

- **Web API** — FastAPI + WebSocket + JWT 认证
- **Dashboard 升级** — 内容日历、AI 对话页面、移动端适配
- **用户系统** — PostgreSQL + 多用户隔离 + RBAC
- **插件市场** — PyPI 标签 `agentcrew-skill` / `agentcrew-platform`
- **内容策略** — 日历视图、系列管理、话题库 UI

### 增长：社区生态 (Growth: Community Ecosystem)

> **目标**: 从个人项目升级为社区驱动的开源项目。

- 🧩 社区插件市场发布（与工程插件系统同步）
- 🏆 贡献者认可计划（Hall of Fame + swag）
- 💰 GitHub Sponsors / Open Collective 设置
- 🎤 PyCon / AI 会议演讲（建立行业信誉）
- 📰 社区月刊（由 AgentCrew 自己撰写和发布）

---

## Phase 5: v2.0 — Commercialization（商业化）

> **目标**: 可运营的 SaaS 产品。

- **SaaS 部署** — Kubernetes Helm Chart、多租户
- **付费计划** — Free / Pro (¥99/月) / Team (¥499/月) / Enterprise
- **高级分析** — ROI 分析、竞品监控、趋势预测、A/B 测试
- **Agent 协作** — Agent 间消息传递、每日站报推送到飞书/钉钉
- **企业特性** — SSO、审计日志、私有部署、白标

### 增长：商业规模 (Growth: Commercial Scale)

> **目标**: 从开源工具转型为可持续的商业产品。

- 📄 客户成功案例白皮书和企业案例研究
- 🤝 合作伙伴生态和集成市场
- 🏢 内容营销代理合作
- 📊 公开基准报告（定位为行业思想领袖）

---

## Dogfooding Tracker（自推广闭环）

AgentCrew 的核心叙事：让项目自己推广自己。以下记录所有用 AgentCrew 自身发布的内容和效果。

### 已发布内容

| 日期 | 平台 | 标题 | 链接 | 效果 |
|------|------|------|------|------|
| 2026-07 | 掘金 | AgentCrew MCN 介绍 | [juejin.cn](https://juejin.cn/post/7663435750386303027) | - |

### 计划发布（优先级排序）

1. 🎯 "我写了一个能自己推广自己的 AI 营销团队" — 掘金首篇 Dogfooding 文章（v0.3）
2. 📊 "AgentCrew 技术架构深度解析" — 掘金（v0.3）
3. 🌍 "How AI agents automate my content marketing" — Dev.to（v0.3）
4. 📈 "AgentCrew 如何建立自己的受众——Dogfooding 案例研究" — 多平台（v0.4）
5. 更多话题见 `agentcrew_topics.txt`

### 关键指标

| 指标 | 当前 | v0.5 目标 | v1.0 目标 |
|------|------|-----------|-----------|
| GitHub Stars | 1 | 500 | 2,000 |
| PyPI 下载量 | - | 100/月 | 1,000/月 |
| 掘金文章阅读 | - | 10,000+ | 100,000+ |
| 外部引用/帖子 | 0 | 10+ | 50+ |
| 社区贡献者 | 1 | 5+ | 20+ |

---

## 技术债务清理（贯穿所有阶段）

| 项目 | 阶段 | 说明 |
|------|------|------|
| 类型标注完善 | v0.3 | mypy strict mode |
| 测试覆盖率 > 80% | v0.3-v0.4 | 补齐边界用例 |
| 异步改造 | v0.4 | asyncio 全面替代同步 |
| 结构化日志 | v0.3 | structlog / JSON |
| 性能优化 | v1.0 | LLM 缓存、RAG 加速 |
| 安全审计 | v1.0 | Cookie 加密、Key 轮换 |

---

## 优先级矩阵

```
                    影响力
              低        中        高
          ┌─────────┬─────────┬─────────┐
    高    │         │ 新平台   │ 错误重试 │
实         │         │ 图片生成 │ 持久调度 │
施   ├─────────┼─────────┼─────────┤
难   中    │ CI/CD   │ 多模型   │ 内容审核 │
度         │ 已知Bug │ 智能排期 │ Web API  │
     ├─────────┼─────────┼─────────┤
    低    │ 代码清理 │ 跨平台适配│ 动态Skill│
          │         │         │          │
          └─────────┴─────────┴─────────┘
```

执行顺序: 左上 → 右上 → 中中 → 右下

### 增长与可见性矩阵 (Growth & Visibility)

```
                    影响力
              低        中        高
          ┌─────────┬─────────┬─────────┐
    高    │         │ PH发布   │         │
实         │         │ HN Show  │         │
施   ├─────────┼─────────┼─────────┤
难   中    │ Issue   │ Demo录制 │ Topics  │
度         │ 模板    │ 社区发帖 │ Docker  │
     ├─────────┼─────────┼─────────┤
    低    │ Keywords│ 截图     │ Badges  │
          │ Discussions│      │ 掘金文章 │
          └─────────┴─────────┴─────────┘
```

增长执行顺序: 右下 → 中右 → 左下 → 中中 → 上中

---

## 下一个迭代：v0.3 任务清单

> 按 ROI 排序，`🔧` = 工程任务，`📈` = 增长任务。先做高 ROI 低投入的增长任务建立势头。

1. 📈 **GitHub Topics** — 添加 15+ 精选 topics，开启仓库可发现性（10 分钟，最高 ROI）
2. 📈 **README Badges** — CI status + 测试覆盖率 + PyPI 下载量 badge（5 分钟，workflows 已存在）
3. 📈 **pyproject.toml keywords** — 扩展 12+ 关键词提升 PyPI 搜索排名（3 分钟）
4. 🔧 **Reviewer Agent** — 发布前内容审核（新 Agent）
5. 📈 **掘金介绍文章** — Dogfooding：用项目自身发布介绍文章（30 分钟）
6. 📈 **终端 Demo 录制** — 30s asciicast/GIF 展示 pip install → 第一条发布（20 分钟）
7. 📈 **Dashboard 截图** — 放到 README 第一屏，留住 80% 浏览者（15 分钟）
8. 🔧 **重试机制** — BaseAgent + PlatformAdapter 层指数退避
9. 🔧 **持久化调度** — SQLite 存储 + `schedule resume` 命令
10. 🔧 **Docker 部署** — Dockerfile + docker-compose.yml（同时降低上手门槛）
11. 📈 **V2EX 发布帖** — 中文开发者社区曝光（20 分钟）
12. 📈 **Reddit r/Python 交叉发帖** — 国际社区曝光（15 分钟）
13. 🔧 **Pre-commit hooks** — ruff + black + mypy
14. 🔧 **修复 test_base.py 警告** — TestAgent 去掉 `__init__`
15. 📈 **Issue 模板** — bug report + feature request 模板（10 分钟）
16. 🔧 **RAG 批量嵌入分批** — 自动 3-5 chunks/次
