"""Test configuration and shared fixtures."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agents.base import Task
from agents.skills import BUILTIN_SKILLS, SkillRegistry
from agents.tools import BUILTIN_TOOLS, ToolRegistry
from llm.client import LLMClient


@pytest.fixture(autouse=True)
def mock_web_search():
    """Mock web_search to avoid real network calls."""
    with patch("duckduckgo_search.DDGS") as mock:
        mock.return_value.__enter__.return_value.text.return_value = []
        yield


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client that returns predictable responses."""
    client = MagicMock(spec=LLMClient)
    client.chat.return_value = "这是一个测试生成的内容。\n\n## 二级标题\n\n这是正文内容。"
    client.chat_stream.return_value = iter(["这是", "测试", "内容"])
    return client


@pytest.fixture
def tool_registry():
    """Create a ToolRegistry with all built-in tools."""
    registry = ToolRegistry()
    for tool in BUILTIN_TOOLS:
        registry.register(tool)
    return registry


@pytest.fixture
def skill_registry():
    """Create a SkillRegistry with all built-in skills."""
    registry = SkillRegistry()
    for skill_class in BUILTIN_SKILLS:
        registry.register(skill_class)
    return registry


@pytest.fixture
def sample_task():
    """Create a sample writing task."""
    return Task(
        task_id="test_001",
        task_type="write",
        params={
            "topic": "Python异步编程",
            "style": "technical",
            "platform": "juejin",
            "enable_rag": False,
        },
    )


@pytest.fixture
def sample_publish_task():
    """Create a sample publishing task."""
    return Task(
        task_id="test_pub_001",
        task_type="publish",
        params={
            "content": {
                "text": "这是一篇测试文章的内容。" * 20,
            },
            "platforms": [],
            "dry_run": True,
        },
    )
