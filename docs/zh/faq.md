# 常见问题

## LLM API 相关

**Q: 提示 "LLM API key not configured"？**

编辑 `.env`，设置 `DEEPSEEK_API_KEY=sk-...`。

**Q: 支持哪些 LLM？**

DeepSeek, OpenAI, Anthropic, Ollama, 以及任何 OpenAI-compatible API。

**Q: 如何切换 LLM？**

```python
from llm.client import create_llm_client
client = create_llm_client("openai", api_key="sk-...")
```

## 平台相关

**Q: 如何获取掘金 Cookie？**

浏览器 F12 → Application → Cookies → juejin.cn → 复制全部。

**Q: 知乎发布需要什么？**

Playwright + Cookie。首次需要 GUI 环境手动登录保存 Cookie。

**Q: Dev.to API key 在哪？**

https://dev.to/settings/extensions → Generate API key。

## 发布相关

**Q: 发布失败怎么办？**

自动重试 3 次（指数退避）。查看 `data/post_history.json` 了解失败原因。

**Q: 如何预览不发布？**

加 `--dry-run` 参数。

## 调度相关

**Q: 重启后任务丢失？**

不会。任务持久化在 `data/scheduler.json`。用 `schedule resume` 恢复。

**Q: 支持 cron 吗？**

支持。`--cron "0 9 * * 1-5"`。

## RAG 相关

**Q: RAG 批量嵌入 OOM？**

硅基流动 BGE 模型限制。分批 3-5 chunks/次。

## Docker 相关

**Q: Docker 如何安装？**

```bash
cp .env.example .env  # 编辑 API keys
docker compose up dashboard
```
