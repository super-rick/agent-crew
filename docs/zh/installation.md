[:us: English](/installation/)<br><br># 安装配置

## 环境要求

- Python 3.10+
- pip

## 安装

### pip（推荐）

```bash
pip install agentcrew-mcn
```

### 源码

```bash
git clone https://github.com/super-rick/agentcrew-mcn.git
cd agentcrew-mcn
pip install -r requirements.txt
```

### Docker

```bash
docker compose run --rm cli write generate -t "Hello World"
```

## 配置

```bash
agentcrew-mcn init    # 创建 config.yaml + .env 模板
```

编辑 `.env`，至少填入一个 LLM API key：

```bash
DEEPSEEK_API_KEY=sk-your-key
```

### LLM Provider

| Provider | 环境变量 | 默认 Model |
|----------|----------|-----------|
| DeepSeek | `DEEPSEEK_API_KEY` | deepseek-chat |
| OpenAI | `OPENAI_API_KEY` | gpt-4o |
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet-5 |
| Ollama | 无需（本地） | llama3 |

### 平台认证

详见 [平台配置](platforms/index.md)。各平台需要 Cookie / API Key / OAuth 等不同方式。

## 验证

```bash
agentcrew-mcn --help
agentcrew-mcn write generate -t "测试" --dry-run
```

## 升级

```bash
pip install --upgrade agentcrew-mcn
```
