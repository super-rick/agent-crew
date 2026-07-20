[🇨🇳 中文](zh/scheduling/){ .md-button }

# Scheduling

Auto-publish on schedule with interval, cron, and smart scheduling.

## Commands

```bash
agentcrew-mcn schedule start -f topics.txt -p juejin -i 6
agentcrew-mcn schedule start -f topics.txt -p juejin --cron "0 9 * * 1-5"
agentcrew-mcn schedule resume
agentcrew-mcn schedule status
agentcrew-mcn schedule stop
```

## Persistence

Tasks saved to `data/scheduler.json`. Restore with `schedule resume` after restart.

## Smart Scheduling

Analyst Agent analyzes history to find best publish times:

```python
analyst = AnalystAgent(llm_client)
best_hours = analyst.predict_best_times(platform="devto")  # [15, 17, 12]
scheduler.set_smart_schedule(best_hours, tasks)
```

Defaults when no data:

| Platform | Default Hours |
|----------|---------------|
| Juejin | 8, 12, 20 |
| Zhihu | 10, 15, 21 |
| Dev.to | 15, 17, 12 |

## Anti-Detection

Random jitter (±30min) prevents fixed-interval detection.

## Cron Examples

```bash
--cron "0 9 * * *"     # Daily 9:00 AM
--cron "0 */6 * * *"   # Every 6 hours
--cron "0 9 * * 1-5"   # Weekdays 9:00 AM
```
