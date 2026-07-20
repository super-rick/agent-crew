# FAQ

## LLM

**Q: "LLM API key not configured"?**

Edit `.env`, set `DEEPSEEK_API_KEY=sk-...`.

**Q: Supported LLMs?**

DeepSeek, OpenAI, Anthropic, Ollama, OpenAI-compatible.

## Platforms

**Q: How to get Juejin Cookie?**

Browser F12 → Application → Cookies → juejin.cn → copy all.

**Q: Dev.to API key?**

https://dev.to/settings/extensions → Generate API key.

## Publishing

**Q: Publish failed?**

Auto-retries 3 times (exponential backoff). Check `data/post_history.json`.

**Q: Preview without publishing?**

Use `--dry-run` flag.

## Scheduling

**Q: Tasks lost after restart?**

No. Persisted in `data/scheduler.json`. Use `schedule resume`.

**Q: Cron support?**

Yes. `--cron "0 9 * * 1-5"`.

## Docker

```bash
cp .env.example .env
docker compose up dashboard
```
