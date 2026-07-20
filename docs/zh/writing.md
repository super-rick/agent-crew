[:us: English](/writing/){ .md-button }

# 内容创作

Writer Agent 负责 AI 内容生成，支持多风格、多平台。

## 命令

```bash
agentcrew-mcn write generate -t "Python async"                  # 基本
agentcrew-mcn write generate -t "AI 入门" -p juejin -s technical # 指定平台/风格
agentcrew-mcn write generate -t "Python" --rag                  # RAG 增强
agentcrew-mcn write generate -t "AI" --skill trending_writing   # 使用 Skill
agentcrew-mcn write generate -t "Test" --dry-run                # 预览模式
agentcrew-mcn write outline -t "Python async"                   # 只生成大纲
```

## 风格 (-s/--style)

| 风格 | 适合 |
|------|------|
| `technical` | 掘金、Dev.to |
| `casual` | 知乎 |
| `thread` | X/Twitter |
| `promotional` | 项目推广 |

## 平台 (-p/--platform)

生成时自动适配平台风格。掘金 = 技术深度 + 代码示例，知乎 = 观点 + 故事化，Dev.to = 英文版。

## 跨平台生成

```python
writer.cross_platform_generate("Python async", platforms=["juejin", "zhihu", "devto"])
# => {"juejin": "...", "zhihu": "...", "devto": "..."}
```

## 封面图

```python
cover = writer.generate_cover_image("Python async", "technical")
# => {"url": "https://...", "model": "dall-e-3"}
```

需要 `OPENAI_API_KEY`。

## Skill

内置 Skill：`trending_writing`, `technical_article`, `thread_writing`, `research_and_write`（LLM 自主编排）。
