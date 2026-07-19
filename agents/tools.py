"""
Tool system — atomic operations that Agents can invoke.

Tool = 原子操作，每个 Tool 只做一件事。
Agent 通过 ToolRegistry 管理自己的工具集。

Tool 的设计遵循 OpenAI Function Calling 格式，
to_openai_function() 方法可直接用于 LLM 的 tool_choice。
"""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    """A standardized atomic operation that an Agent can invoke.

    Attributes:
        name: Unique identifier, e.g. "web_search"
        description: Human-readable description for the LLM to understand when to use
        parameters: JSON Schema for the tool's parameters
        func: The actual callable that executes the tool
    """

    name: str
    description: str
    parameters: dict
    func: Callable[..., Any]

    def to_openai_function(self) -> dict:
        """Convert to OpenAI Function Calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def execute(self, **kwargs) -> Any:
        """Execute the tool with given arguments."""
        return self.func(**kwargs)


class ToolRegistry:
    """Registry that manages an Agent's Tools.

    Each Agent instance has its own ToolRegistry.
    Tools are registered at Agent initialization time.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool. Overwrites if name already exists."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        """Get a tool by name. Raises KeyError if not found."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found. Available: {self.list_names()}")
        return self._tools[name]

    def list_tools(self) -> list[Tool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        """Return names of all registered tools."""
        return list(self._tools.keys())

    def get_openai_functions(self) -> list[dict]:
        """Convert all registered tools to OpenAI function format."""
        return [tool.to_openai_function() for tool in self._tools.values()]

    def describe_all(self) -> str:
        """Return a human-readable description of all registered tools."""
        lines = []
        for name, tool in self._tools.items():
            params_desc = tool.description or "no description"
            lines.append(f"  {name}: {params_desc}")
        return "\n".join(lines)

    def execute(self, name: str, **kwargs) -> Any:
        """Execute a tool by name with given arguments."""
        tool = self.get(name)
        return tool.execute(**kwargs)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# ============================================================
# Built-in Tools
# ============================================================


def _web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using DuckDuckGo (no API key required).

    Returns a list of dicts with 'title', 'url', 'snippet' keys.
    """
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    }
                )
        return results
    except ImportError:
        return [
            {
                "title": "DuckDuckGo search unavailable",
                "url": "",
                "snippet": "Install duckduckgo-search package: pip install duckduckgo-search",
            }
        ]


def _fetch_url_content(url: str) -> str:
    """Fetch content from a URL. Returns the text content."""
    import httpx

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(url, follow_redirects=True)
            response.raise_for_status()
            # Return first 8000 chars to avoid overwhelming the LLM
            return response.text[:8000]
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"


def _get_current_time() -> str:
    """Return the current date and time as ISO format string."""
    from datetime import datetime

    return datetime.now().isoformat()


def _generate_image(
    prompt: str,
    size: str = "1024x1024",
    style: str = "vivid",
    api_key: str = "",
    base_url: str = "",
) -> dict:
    """Generate an image using OpenAI DALL-E API.

    Uses the same API key/url as the LLM client if not specified.
    Falls back to DEEPSEEK_API_KEY / OPENAI_API_KEY env vars.

    Returns dict with:
        - url: image URL (most common)
        - b64_json: base64 data (if response_format=b64_json, not used by default)
        - revised_prompt: DALL-E revised prompt
        - model: model used
    """
    import os

    key = api_key or os.environ.get("OPENAI_API_KEY", "") or os.environ.get("DEEPSEEK_API_KEY", "")
    url = base_url or ""
    if not key:
        return {"error": "No API key configured. Set OPENAI_API_KEY in .env."}

    try:
        from openai import OpenAI

        kwargs = {"api_key": key}
        if url:
            kwargs["base_url"] = url
        client = OpenAI(**kwargs)

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            style=style,
            n=1,
        )
        img = response.data[0]
        return {
            "url": img.url,
            "revised_prompt": getattr(img, "revised_prompt", prompt),
            "model": "dall-e-3",
            "size": size,
        }
    except Exception as e:
        return {"error": str(e), "prompt": prompt[:100]}


# ============================================================
# Built-in Tool Definitions
# ============================================================

BUILTIN_TOOLS: list[Tool] = [
    Tool(
        name="web_search",
        description="搜索互联网获取最新信息。在需要了解当前热点、最新技术趋势时使用。",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数，默认5",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        func=_web_search,
    ),
    Tool(
        name="fetch_url_content",
        description="获取指定URL的网页内容。在需要阅读某篇文章或页面详情时使用。",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要获取内容的URL",
                },
            },
            "required": ["url"],
        },
        func=_fetch_url_content,
    ),
    Tool(
        name="get_current_time",
        description="获取当前日期和时间。在需要知道当前时间以决定内容策略时使用。",
        parameters={
            "type": "object",
            "properties": {},
        },
        func=_get_current_time,
    ),
    Tool(
        name="generate_image",
        description=(
            "使用 DALL-E 生成封面图或插图。"
            "在需要为文章生成封面图、配图时使用。"
            "支持 DALL-E 3 高质量生成。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "图片描述（英文效果更好），" "如 'A futuristic AI robot writing at a desk'"
                    ),
                },
                "size": {
                    "type": "string",
                    "description": "图片尺寸",
                    "enum": ["1024x1024", "1024x1792", "1792x1024"],
                    "default": "1024x1024",
                },
                "style": {
                    "type": "string",
                    "description": "图片风格",
                    "enum": ["vivid", "natural"],
                    "default": "vivid",
                },
            },
            "required": ["prompt"],
        },
        func=_generate_image,
    ),
]
