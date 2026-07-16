# Contributing to AgentCrew

感谢你对 AgentCrew 的关注！本文档将帮助你快速上手贡献代码。

## 开发环境设置

```bash
# 1. Fork + Clone
git clone https://github.com/YOUR_USERNAME/agent-crew.git
cd agent-crew

# 2. 创建虚拟环境（需要 Python 3.10+）
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化配置
python -m cli.main init

# 5. 编辑 .env，填入 API Key
#    DEEPSEEK_API_KEY=sk-...

# 6. 运行测试确认一切正常
pytest tests/ -v
```

## 项目架构

在开始之前，建议先阅读 [README.md](README.md) 的架构概览。核心概念：

```
Agent（AI 员工）  →  每个 Agent 有独立的 Tool 和 Skill 注册表
Tool（原子操作）   →  web_search, fetch_url, get_current_time
Skill（Tool 编排） →  按特定顺序调用 Tools 完成复杂任务
Platform Adapter   →  对每个平台实现 authenticate() + post()
Orchestrator       →  任务分派 + 调度引擎
```

## 可以贡献什么？

### 1. 添加新平台适配器

想让 AgentCrew 支持新的内容平台（如小红书、Medium、Dev.to）？只需实现两个方法：

```python
# platforms/myplatform.py
from platforms.base import BasePlatformAdapter, ContentPost, PostResult, PlatformStatus

class MyPlatformAdapter(BasePlatformAdapter):
    def authenticate(self) -> bool:
        """验证身份。返回 True/False。"""
        ...

    def post(self, content: ContentPost, dry_run: bool = False) -> PostResult:
        """发布内容。dry_run=True 时不实际发布。"""
        ...

    def get_status(self) -> PlatformStatus:
        """返回认证状态和速率限制。"""
        ...
```

参考已有的 `platforms/juejin.py`（API 方式）和 `platforms/zhihu.py`（Playwright 方式）。

然后在 `cli/main.py` 的 `setup_orchestrator()` 中注册：

```python
elif platform_name == "myplatform":
    from platforms.myplatform import MyPlatformAdapter
    publisher.register_platform(platform_name, MyPlatformAdapter(plat_cfg))
```

### 2. 添加新 Skill

Skill 是一组 Tool 的有序执行管道：

```python
# agents/skills.py
class MySkill(Skill):
    name = "my_skill"
    description = "描述这个 Skill 做什么"

    def execute(self, registry: ToolRegistry, params: dict) -> dict:
        # 调用 Tools 完成你的逻辑
        result1 = registry.call("tool_name", **params)
        result2 = registry.call("another_tool", context=result1)
        return {"output": result2}
```

### 3. 添加新 Tool

Tool 是原子操作，会自动转为 OpenAI Function Calling 格式：

```python
# agents/tools.py
my_tool = Tool(
    name="my_tool",
    description="这个工具做什么",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "查询参数"}
        },
        "required": ["query"]
    },
    handler=lambda query: f"Result for {query}",
)
```

### 4. 修复 Bug 或改进文档

查看 [Issues](https://github.com/super-rick/agent-crew/issues) 中的 `good first issue` 标签。

## 提交 PR 流程

1. **Fork** 本仓库
2. 创建分支：`git checkout -b feat/my-feature`
3. 写代码 + 测试：`pytest tests/ -v`
4. 格式化：`make fmt`
5. 提交：`git commit -m "feat: 描述你的改动"`
6. Push + 创建 Pull Request

## 代码风格

- Python 3.10+（可使用 `X | None` 语法）
- 用 `black` 格式化，`ruff` 检查
- 行宽 100 字符
- 测试用 `unittest.mock` mock 外部依赖（LLM / 网络）
- Commit message 用中文或英文都可以，推荐 [Conventional Commits](https://www.conventionalcommits.org/)

## 测试指南

```bash
# 全部测试
pytest tests/ -v

# 单个模块
pytest tests/test_agents/test_writer.py -v
pytest tests/test_platforms/ -v
pytest tests/test_integration/ -v
```

测试使用 `conftest.py` 中的 autouse fixtures 自动 mock 了 LLM 和网络调用，你不需要真实的 API Key 就能跑测试。

## 问题反馈

- 🐛 Bug → [GitHub Issues](https://github.com/super-rick/agent-crew/issues)
- 💡 功能建议 → [GitHub Discussions](https://github.com/super-rick/agent-crew/discussions)
- ❓ 使用问题 → 同上

---

再次感谢你的贡献！🎉
