"""
Translation table for AgentCrew CLI messages.

Each key maps to a dict with at minimum {"zh": ..., "en": ...}.
Keys use dot-separated segments: category.subcategory.specific

Adding new messages:
    1. Add a key + translations here
    2. Use `_(key, **kwargs)` in code
    3. kwargs become .format() variables in the template string
"""

from __future__ import annotations

MESSAGES: dict[str, dict | str] = {
    # ============================================================
    # CLI — Top-level
    # ============================================================
    "cli.description": {
        "zh": (
            "AgentCrew MCN — AI MCN 自动推广工具。\n\n"
            "你的 AI 营销团队，24 小时在线工作，不领工资。\n\n"
            "使用方式:\n"
            '    agentcrew-mcn write generate --topic "主题"\n'
            '    agentcrew-mcn publish post --content "内容" --platform juejin\n'
            "    agentcrew-mcn schedule start --topic-file topics.txt\n"
            "    agentcrew-mcn rag ingest --file document.md\n\n"
            "首次使用:\n"
            "    agentcrew-mcn init          # 创建配置文件模板\n"
            "    # 编辑 .env，填入 API Key\n"
            '    agentcrew-mcn write generate --topic "Hello World"'
        ),
        "en": (
            "AgentCrew MCN — AI-powered content marketing automation.\n\n"
            "Your AI marketing team, working 24/7, never asks for a raise.\n\n"
            "Usage:\n"
            '    agentcrew-mcn write generate --topic "Your Topic"\n'
            '    agentcrew-mcn publish post --content "Content" --platform devto\n'
            "    agentcrew-mcn schedule start --topic-file topics.txt\n"
            "    agentcrew-mcn rag ingest --file document.md\n\n"
            "First time:\n"
            "    agentcrew-mcn init          # Create config files\n"
            "    # Edit .env, add your API Key\n"
            '    agentcrew-mcn write generate --topic "Hello World"'
        ),
    },
    "cli.config_loaded": {
        "zh": "使用配置: {path}",
        "en": "Using config: {path}",
    },
    # ============================================================
    # Error messages
    # ============================================================
    "error.init_failed": {
        "zh": "❌ 初始化失败: {error}\n💡 提示: 检查 config.yaml 和 .env 设置",
        "en": (
            "❌ Initialization failed: {error}\n"
            "💡 Hint: Check your config.yaml and .env settings"
        ),
    },
    "error.no_api_key": {
        "zh": (
            "❌ LLM API Key 未配置\n"
            "   原因: 未找到 {key_name} 环境变量\n"
            "   解决:\n"
            "     1. 运行 [bold]agentcrew-mcn init --wizard[/bold] 交互式配置\n"
            "     2. 或编辑 .env 文件，添加: {key_name}=sk-...\n"
            "     3. 去 {provider_url} 获取 API Key"
        ),
        "en": (
            "❌ LLM API key not configured\n"
            "   Reason: {key_name} environment variable not found\n"
            "   Fix:\n"
            "     1. Run [bold]agentcrew-mcn init --wizard[/bold] for interactive setup\n"
            "     2. Or edit your .env file, add: {key_name}=sk-...\n"
            "     3. Get an API key at {provider_url}"
        ),
    },
    "error.no_config": {
        "zh": (
            "未找到配置文件。\n\n"
            "已搜索:\n"
            "  • ./config.yaml\n"
            "  • ~/.config/agentcrew-mcn/config.yaml\n"
            "  • ~/.agentcrew-mcn/config.yaml\n\n"
            "[bold]运行以下命令开始:[/bold]\n"
            "  [cyan]agentcrew-mcn init[/cyan]\n\n"
            "或指定配置文件:\n"
            "  [cyan]agentcrew-mcn --config /path/to/config.yaml write generate ...[/cyan]"
        ),
        "en": (
            "No configuration file found.\n\n"
            "Searched:\n"
            "  • ./config.yaml\n"
            "  • ~/.config/agentcrew-mcn/config.yaml\n"
            "  • ~/.agentcrew-mcn/config.yaml\n\n"
            "[bold]Run this to get started:[/bold]\n"
            "  [cyan]agentcrew-mcn init[/cyan]\n\n"
            "Or specify a config file explicitly:\n"
            "  [cyan]agentcrew-mcn --config /path/to/config.yaml write generate ...[/cyan]"
        ),
    },
    "warn.rag_disabled": {
        "zh": "⚠ RAG 未启用: {reason}",
        "en": "⚠ RAG not enabled: {reason}",
    },
    "warn.mcp_skipped": {
        "zh": "⚠ MCP 客户端初始化已跳过: {reason}",
        "en": "⚠ MCP client init skipped: {reason}",
    },
    "warn.mcp_not_installed": {
        "zh": "⚠ MCP SDK 未安装。运行 [bold]pip install mcp[/bold] 以启用 MCP 客户端支持。",
        "en": (
            "⚠ MCP SDK not installed. "
            "Run [bold]pip install mcp[/bold] to enable MCP client support."
        ),
    },
    "warn.platform_not_loaded": {
        "zh": "  ⚠ 平台 '{name}' 未加载: {error}",
        "en": "  ⚠ Platform '{name}' not loaded: {error}",
    },
    "ok.mcp_connected": {
        "zh": (
            "✓ MCP: [bold]{count}[/bold] 个服务器已连接, "
            "[bold]{tools}[/bold] 个工具已注册{skipped}"
        ),
        "en": (
            "✓ MCP: [bold]{count}[/bold] server(s) connected, "
            "[bold]{tools}[/bold] tool(s) registered{skipped}"
        ),
    },
    "ok.mcp_skipped_conflict": {
        "zh": " ([dim]{count} 个因名称冲突被跳过[/dim])",
        "en": " ([dim]{count} skipped due to name conflict[/dim])",
    },
    # ============================================================
    # Init command
    # ============================================================
    "init.overwrite_warning": {
        "zh": "以下文件已存在:",
        "en": "The following files already exist:",
    },
    "init.overwrite_confirm": {
        "zh": "是否覆盖?",
        "en": "Overwrite them?",
    },
    "init.aborted": {
        "zh": "已取消。",
        "en": "Aborted.",
    },
    "init.created": {
        "zh": "✓ 已创建: {path}",
        "en": "✓ Created: {path}",
    },
    "init.next_steps_title": {
        "zh": "下一步",
        "en": "Next Steps",
    },
    "init.step1": {
        "zh": "1. 编辑 [cyan].env[/cyan] 并填入 API Key:",
        "en": "1. Edit [cyan].env[/cyan] and add your API keys:",
    },
    "init.step2": {
        "zh": "2. 开始生成内容:",
        "en": "2. Start generating content:",
    },
    "init.step3": {
        "zh": "3. 探索更多命令:",
        "en": "3. Explore all commands:",
    },
    # ============================================================
    # Doctor command
    # ============================================================
    "doctor.title": {
        "zh": "🔍 AgentCrew 健康检查",
        "en": "🔍 AgentCrew Health Check",
    },
    "doctor.config_file": {
        "zh": "配置文件",
        "en": "Config file",
    },
    "doctor.env_file": {
        "zh": ".env 文件",
        "en": ".env file",
    },
    "doctor.llm": {
        "zh": "LLM ({provider})",
        "en": "LLM ({provider})",
    },
    "doctor.rag": {
        "zh": "RAG ({provider})",
        "en": "RAG ({provider})",
    },
    "doctor.chromadb": {
        "zh": "ChromaDB",
        "en": "ChromaDB",
    },
    "doctor.playwright": {
        "zh": "Playwright",
        "en": "Playwright",
    },
    "doctor.mcp_server": {
        "zh": "MCP Server",
        "en": "MCP Server",
    },
    "doctor.summary": {
        "zh": "{problems} 个问题, {fatal} 个致命。运行 agentcrew-mcn init --wizard 可重新配置。",
        "en": (
            "{problems} issue(s), {fatal} fatal. "
            "Run: agentcrew-mcn init --wizard to reconfigure."
        ),
    },
    "doctor.summary_ok": {
        "zh": "🎉 一切正常! 运行 agentcrew-mcn write generate 开始写作。",
        "en": "🎉 All good! Run: agentcrew-mcn write generate to start writing.",
    },
    "doctor.not_found": {
        "zh": "未找到",
        "en": "Not found",
    },
    "doctor.env_not_found": {
        "zh": "与 config.yaml 不在同一目录",
        "en": "Not found alongside config",
    },
    "doctor.quick_mode": {
        "zh": "--quick 模式: 跳过网络检查",
        "en": "--quick mode: skipping network checks",
    },
    "doctor.fix_init": {
        "zh": "运行 agentcrew-mcn init",
        "en": "Run: agentcrew-mcn init",
    },
    "doctor.fix_embedding_error": {
        "zh": "设置 EMBEDDING_API_KEY 或改用 provider: local → 查看 .env.example",
        "en": "Set EMBEDDING_API_KEY or use provider: local → See .env.example",
    },
    "doctor.fix_embedding_config": {
        "zh": "设置 rag.embedding.provider: local 或配置 API key → 查看 .env.example",
        "en": "Set rag.embedding.provider: local or configure API key → See .env.example",
    },
    "doctor.llm_ok": {
        "zh": "✅ API Key 有效{balance}",
        "en": "✅ API key valid{balance}",
    },
    "doctor.llm_balance": {
        "zh": ", 余额 ¥{balance}",
        "en": ", balance ${balance}",
    },
    "doctor.llm_no_key": {
        "zh": "❌ 未配置 API Key → 编辑 .env, 设置 {key_name}=sk-...",
        "en": "❌ No API key → Edit .env, set {key_name}=sk-...",
    },
    "doctor.llm_auth_failed": {
        "zh": "❌ API Key 验证失败 ({error}) → 检查 key 是否正确，或去 {url} 重新生成",
        "en": "❌ API key validation failed ({error}) → Check your key or regenerate at {url}",
    },
    "doctor.platform_ok": {
        "zh": "✅ Cookie 有效{user}",
        "en": "✅ Cookie valid{user}",
    },
    "doctor.platform_user": {
        "zh": "（用户: {user}）",
        "en": " (user: {user})",
    },
    "doctor.platform_expired": {
        "zh": "❌ Cookie 已过期 → 运行 agentcrew-mcn auth {platform} --browser 重新获取",
        "en": "❌ Cookie expired → Run: agentcrew-mcn auth {platform} --browser",
    },
    "doctor.platform_no_key": {
        "zh": "❌ 未配置 → 运行 agentcrew-mcn auth {platform} 设置",
        "en": "❌ Not configured → Run: agentcrew-mcn auth {platform}",
    },
    "doctor.platform_auth_failed": {
        "zh": "❌ 认证失败 ({error}) → {fix}",
        "en": "❌ Auth failed ({error}) → {fix}",
    },
    "doctor.rag_ok": {
        "zh": "✅ 嵌入服务可用",
        "en": "✅ Embedding service available",
    },
    "doctor.rag_failed": {
        "zh": "⚠️ 嵌入服务异常: {error} → {fix}",
        "en": "⚠️ Embedding service error: {error} → {fix}",
    },
    "doctor.chromadb_ok": {
        "zh": "✅ {count} 条文档, {size}",
        "en": "✅ {count} documents, {size}",
    },
    "doctor.chromadb_empty": {
        "zh": "ℹ️ 空知识库 — 运行 agentcrew-mcn rag ingest --file doc.md 导入文档",
        "en": "ℹ️ Empty — Run: agentcrew-mcn rag ingest --file doc.md to add documents",
    },
    "doctor.playwright_ok": {
        "zh": "✅ Chromium 已安装",
        "en": "✅ Chromium installed",
    },
    "doctor.playwright_missing": {
        "zh": "⚠️ 未安装 → pip install playwright && playwright install chromium",
        "en": "⚠️ Not installed → pip install playwright && playwright install chromium",
    },
    "doctor.mcp_disabled": {
        "zh": "ℹ️ 未启用（在 config.yaml 的 mcp.server.enabled 设置）",
        "en": "ℹ️ Disabled (set mcp.server.enabled in config.yaml)",
    },
    "doctor.mcp_ok": {
        "zh": "✅ 已启用 ({transport})",
        "en": "✅ Enabled ({transport})",
    },
    # ============================================================
    # Write command
    # ============================================================
    "write.generate.help": {
        "zh": (
            "生成一篇内容（完整文章/帖子/Thread）\n\n"
            "📖 示例:\n"
            '  agentcrew-mcn write generate -t "Python 异步编程" -p juejin\n'
            '  agentcrew-mcn write generate -t "AI 会替代程序员吗" -s casual -p zhihu\n'
            '  agentcrew-mcn write generate -t "AgentCrew 架构" --rag\n'
            '  agentcrew-mcn write generate -t "开源工具推荐" -P README.md\n\n'
            "💡 提示: 首次使用？运行 agentcrew-mcn init --wizard 完成初始化\n"
            "📚 更多示例: agentcrew-mcn help write"
        ),
        "en": (
            "Generate content (full article / post / thread)\n\n"
            "📖 Examples:\n"
            '  agentcrew-mcn write generate -t "Python Async Programming" -p devto\n'
            '  agentcrew-mcn write generate -t "Will AI replace developers?" -s casual\n'
            '  agentcrew-mcn write generate -t "My Project Architecture" --rag\n'
            '  agentcrew-mcn write generate -t "Open Source Tools" -P README.md\n\n'
            "💡 First time? Run: agentcrew-mcn init --wizard\n"
            "📚 More examples: agentcrew-mcn help write"
        ),
    },
    "write.style.technical": {
        "zh": "深度技术文章，结构清晰，带示例代码（适合掘金/Dev.to）",
        "en": "In-depth technical article with code examples (for Dev.to/Juejin)",
    },
    "write.style.casual": {
        "zh": "轻松友好的科普帖，用比喻解释概念（适合知乎）",
        "en": "Friendly explainer post, using analogies (for Zhihu/blogs)",
    },
    "write.style.thread": {
        "zh": "多帖 Thread，每帖一个要点，有钩子（适合 X/Twitter）",
        "en": "Multi-post thread, one key point per post (for X/Twitter)",
    },
    "write.style.promotional": {
        "zh": "推广型内容，突出项目价值和使用场景",
        "en": "Promotional content, highlighting project value and use cases",
    },
    # ============================================================
    # Publish command
    # ============================================================
    "publish.post.help": {
        "zh": (
            "发布内容到指定平台\n\n"
            "📖 示例:\n"
            '  agentcrew-mcn publish post -t "内容..." -p juejin\n'
            "  agentcrew-mcn publish post -f article.md -p juejin -p zhihu\n"
            "  agentcrew-mcn publish post -f article.md -p devto --dry-run\n"
            '  agentcrew-mcn publish post -t "沸点内容" -p juejin\n\n'
            "💡 带 --title 时发布为文章，不带则发布为短内容/沸点"
        ),
        "en": (
            "Post content to target platforms\n\n"
            "📖 Examples:\n"
            '  agentcrew-mcn publish post -t "Content..." -p devto\n'
            "  agentcrew-mcn publish post -f article.md -p juejin -p devto\n"
            "  agentcrew-mcn publish post -f article.md -p devto --dry-run\n"
            '  agentcrew-mcn publish post -t "Short post" -p juejin\n\n'
            "💡 With --title: published as article. Without: short post / pin."
        ),
    },
}
