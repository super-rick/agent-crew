[:us: English](/scheduling/)<br><br># 定时调度

定时自动发布，支持间隔、cron 表达式、智能排期。

## 命令

```bash
# 间隔发布
agentcrew-mcn schedule start -f topics.txt -p juejin -i 6

# Cron 表达式
agentcrew-mcn schedule start -f topics.txt -p juejin --cron "0 9 * * 1-5"

# 从持久化文件恢复
agentcrew-mcn schedule resume

# 状态
agentcrew-mcn schedule status

# 停止
agentcrew-mcn schedule stop
```

## 持久化

任务自动保存到 `data/scheduler.json`。进程重启后 `schedule resume` 恢复。

## 智能排期

Analyst Agent 分析历史数据，推荐最佳发布时间：

```python
analyst = AnalystAgent(llm_client)
best_hours = analyst.predict_best_times(platform="juejin")  # [8, 12, 20]
scheduler.set_smart_schedule(best_hours, tasks)
```

无历史数据时使用各平台合理默认值：

| 平台 | 默认时段 |
|------|----------|
| 掘金 | 8, 12, 20 |
| 知乎 | 10, 15, 21 |
| Dev.to | 15, 17, 12 |

## 反检测

每次发布间隔加随机抖动（±30min），防止平台检测固定频率。

## Cron 示例

```bash
--cron "0 9 * * *"     # 每天 9:00
--cron "0 */6 * * *"   # 每 6 小时
--cron "0 9 * * 1-5"   # 工作日 9:00
```
