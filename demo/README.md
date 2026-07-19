# AgentCrew MCN Demo

终端演示文件 —— 展示 AgentCrew 完整工作流。

## 快速预览

```bash
bash demo/agentcrew-demo.sh
```

## 录制为 asciinema cast

```bash
# 安装 asciinema
brew install asciinema

# 录制
asciinema rec -c "bash demo/agentcrew-demo.sh" demo/agentcrew-demo.cast

# 上传分享
asciinema upload demo/agentcrew-demo.cast
```

## 录制为 GIF

```bash
# 安装工具
brew install asciinema agg

# 录制 cast
asciinema rec -c "bash demo/agentcrew-demo.sh" demo/agentcrew-demo.cast

# 转为 GIF（自定义主题/字体）
agg demo/agentcrew-demo.cast demo/agentcrew-demo.gif \
  --theme monokai \
  --font-family "JetBrains Mono" \
  --font-size 14
```

## 完整工作流录制（需要 API key）

```bash
bash demo/record-demo.sh
```

> 此脚本调用真实的 AgentCrew CLI 命令（需要配置 DEEPSEEK_API_KEY）。
