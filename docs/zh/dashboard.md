[:us: English](/dashboard/){ .md-button }

# Dashboard

Streamlit Web 面板，监控 AI 营销团队。

## 启动

```bash
streamlit run dashboard/app.py
# http://localhost:8501

# Docker
docker compose up dashboard
```

## 页面

| 页面 | 功能 |
|------|------|
| 📈 总览 | KPIs、最近发布、平台分布图、增长指标 |
| 📊 发布分析 | 详细图表、平台过滤 |
| 🤖 AI 分析 | AI 生成的报告和建议 |
| ⚙️ 系统状态 | 连接状态、RAG、配置、日志 |

## 增长指标

Dashboard 内置增长追踪面板（Stars, Version, Tests, Agents），数据来源 [GROWTH.md](https://github.com/super-rick/agentcrew-mcn/blob/main/GROWTH.md)。
