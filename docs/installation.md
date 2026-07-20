[🇨🇳 中文](zh/installation/){ .md-button }

# Installation

## Requirements

- Python 3.10+
- pip

## Install

### pip (recommended)

```bash
pip install agentcrew-mcn
```

### From Source

```bash
git clone https://github.com/super-rick/agentcrew-mcn.git
cd agentcrew-mcn
pip install -r requirements.txt
```

### Docker

```bash
docker compose run --rm cli write generate -t "Hello World"
```

## Configuration

```bash
agentcrew-mcn init    # Creates config.yaml + .env template
```

Edit `.env` with at least one LLM API key:

```bash
DEEPSEEK_API_KEY=sk-your-key
```

### LLM Providers

- **DeepSeek** — `DEEPSEEK_API_KEY` (default)
- **OpenAI** — `OPENAI_API_KEY`
- **Anthropic** — `ANTHROPIC_API_KEY`
- **Ollama** — local, no key needed

### Platform Auth

See [Platform Setup](platforms/index.md). Each platform needs Cookie/API Key/OAuth.

## Verify

```bash
agentcrew-mcn --help
agentcrew-mcn write generate -t "Test" --dry-run
```
