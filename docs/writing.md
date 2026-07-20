[:cn: 中文](/zh/writing/){ .md-button }

# Writing Content

The Writer Agent generates AI content in multiple styles for multiple platforms.

## Commands

```bash
agentcrew-mcn write generate -t "Python async"                  # Basic
agentcrew-mcn write generate -t "AI intro" -p devto -s technical # Platform/style
agentcrew-mcn write generate -t "Python" --rag                  # RAG enhanced
agentcrew-mcn write generate -t "AI" --skill trending_writing   # With Skill
agentcrew-mcn write generate -t "Test" --dry-run                # Preview mode
agentcrew-mcn write outline -t "Python async"                   # Outline only
```

## Styles (`-s/--style`)

| Style | Best For |
|-------|----------|
| `technical` | Juejin, Dev.to |
| `casual` | Zhihu |
| `thread` | X/Twitter |
| `promotional` | Project promotion |

## Cross-Platform Generation

```python
writer.cross_platform_generate("Python async", platforms=["juejin", "zhihu", "devto"])
# => {"juejin": "...", "zhihu": "...", "devto": "..."}
```

## Cover Images

```python
cover = writer.generate_cover_image("Python async", "technical")
# => {"url": "https://...", "model": "dall-e-3"}
```

Requires `OPENAI_API_KEY`.

## Skills

Built-in: `trending_writing`, `technical_article`, `thread_writing`, `research_and_write` (LLM-driven).
