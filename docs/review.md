[🇨🇳 中文](zh/review/){ .md-button }

# Content Review

The Reviewer Agent checks content safety and quality before publishing.

## Review Dimensions

1. **Sensitive Words** — Configurable word list, no built-in defaults
2. **Platform Compliance** — Title/content length, forbidden patterns
3. **Quality Score** — 0-100 across 9 criteria

## Pipeline

```
Writer → Reviewer → Publisher
              ↓ failed
            Skip publish + error
```

## Configuration

```python
reviewer = ReviewerAgent(llm_client, config={
    "reviewer_sensitive_words": {"spam": "spam detected"},
    "reviewer_min_score": 60,
})
```

## Pipeline Usage

```python
task = orchestrator.create_task(
    task_type="write_review_publish",
    params={"topic": "...", "platform": "juejin"}
)
result = orchestrator.execute_pipeline(task)
```
