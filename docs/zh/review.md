[🇺🇸 English](../review/){ .md-button }

# 内容审核

Reviewer Agent 在发布前自动审核内容安全和质量。

## 审核维度

1. **敏感词检测** — 通过配置注入词表
2. **平台规范** — 标题/内容长度、禁止模式
3. **质量评分** — 0-100 分，9 个维度

## 流程

```
Writer → Reviewer → Publisher
              ↓ 不通过
            跳过发布 + 错误信息
```

## 配置

```python
reviewer = ReviewerAgent(llm_client, config={
    "reviewer_sensitive_words": {"加微信": "禁止导流", "赌博": "违规"},
    "reviewer_min_score": 60,  # 最低通过分
})
```

敏感词不从代码内置，全部由使用者配置注入。

## Pipeline 使用

```bash
# 使用 write_review_publish（3 步完整 pipeline）
agentcrew-mcn schedule start -f topics.txt -p juejin
```

代码中：

```python
task = orchestrator.create_task(
    task_type="write_review_publish",
    params={"topic": "...", "platform": "juejin"}
)
result = orchestrator.execute_pipeline(task)
```
