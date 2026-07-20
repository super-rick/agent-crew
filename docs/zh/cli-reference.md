# CLI 参考

完整命令参考。

## write

```bash
agentcrew-mcn write generate -t TOPIC [-s STYLE] [-p PLATFORM] [--rag] [--skill NAME] [--dry-run]
agentcrew-mcn write outline -t TOPIC
```

## publish

```bash
agentcrew-mcn publish post --text TEXT --platform PLATFORM [--dry-run]
agentcrew-mcn publish post --file FILE --platform PLATFORM [--dry-run]
agentcrew-mcn publish status
agentcrew-mcn publish history
```

## schedule

```bash
agentcrew-mcn schedule start -f TOPIC_FILE -p PLATFORM [-i HOURS] [--cron CRON] [--dry-run]
agentcrew-mcn schedule resume [--store PATH] [--dry-run]
agentcrew-mcn schedule status
agentcrew-mcn schedule stop
```

## rag

```bash
agentcrew-mcn rag ingest --file FILE --source NAME
agentcrew-mcn rag search --query QUERY
agentcrew-mcn rag stats
```

## mcp

```bash
agentcrew-mcn mcp serve [--transport stdio|sse] [--port PORT]
agentcrew-mcn mcp list-tools
agentcrew-mcn mcp status
```

## 全局选项

```bash
agentcrew-mcn --help
agentcrew-mcn init
```
