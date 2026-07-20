[🇨🇳 中文](zh/publishing/){ .md-button }

# Publishing

The Publisher Agent distributes content to 9 platforms with automatic retry.

## Commands

```bash
agentcrew-mcn publish post --text "Content..." --platform juejin
agentcrew-mcn publish post --file article.md --platform juejin
agentcrew-mcn publish post --text "Content" --platform juejin --dry-run
agentcrew-mcn publish post --file article.md -p juejin -p zhihu
agentcrew-mcn publish status
agentcrew-mcn publish history
```

## Retry Mechanism

Automatic retry with exponential backoff + jitter:

```
Retry 1: ~1s → Retry 2: ~2s → Retry 3: ~4s
```

## Programmatic API

```python
publisher = PublisherAgent(llm_client)
publisher.register_platform("juejin", JuejinAdapter({"cookie": "..."}))
result = publisher.post_to_platform(text="Content", platform="juejin")
```

## Supported Platforms

Juejin, Zhihu, Dev.to, CSDN, WeChat, SegmentFault, X/Twitter, Xiaohongshu, Medium — 9 platforms. See [Platform Setup](platforms/index.md).
