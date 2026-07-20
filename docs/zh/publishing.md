[:us: English](/publishing/){ .md-button }

# 发布管理

Publisher Agent 负责跨平台内容分发。

## 命令

```bash
agentcrew-mcn publish post --text "内容..." --platform juejin         # 发布文本
agentcrew-mcn publish post --file article.md --platform juejin       # 从文件
agentcrew-mcn publish post --text "内容" --platform juejin --dry-run # 预览
agentcrew-mcn publish post --file article.md -p juejin -p zhihu      # 多平台
agentcrew-mcn publish status                                          # 状态
agentcrew-mcn publish history                                         # 历史
```

## 重试机制

发布失败自动重试（指数退避 + jitter）：

```
重试 1: ~1s → 重试 2: ~2s → 重试 3: ~4s
```

```python
adapter.post_with_retry(content, max_retries=3)
```

## 编程接口

```python
publisher = PublisherAgent(llm_client)
publisher.register_platform("juejin", JuejinAdapter({"cookie": "..."}))
result = publisher.post_to_platform(text="Content", platform="juejin", title="Title")
```

## 支持的平台

掘金、知乎、Dev.to、CSDN、微信公众号、SegmentFault、X/Twitter、小红书、Medium — 共 9 个。详见 [平台配置](platforms/index.md)。
