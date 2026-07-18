"""Tests for the base agent."""

from __future__ import annotations

import pytest

from agents.base import BaseAgent, Task, TaskResult


class TestAgent(BaseAgent):
    """Concrete test agent for testing BaseAgent."""

    name = "test_agent"
    description = "A test agent"

    def get_system_prompt(self) -> str:
        return "You are a test agent."

    def execute(self, task: Task) -> TaskResult:
        return TaskResult(
            task_id=task.task_id,
            success=True,
            data={"message": "done"},
            agent_name=self.name,
        )


class TestBaseAgent:
    """Test suite for BaseAgent."""

    def test_initialization(self, mock_llm_client):
        agent = TestAgent(mock_llm_client, {"key": "value"})
        assert agent.name == "test_agent"
        assert agent.description == "A test agent"
        assert agent.llm_client == mock_llm_client
        assert agent.config == {"key": "value"}

    def test_tool_registry_not_set(self, mock_llm_client):
        agent = TestAgent(mock_llm_client)
        with pytest.raises(RuntimeError, match="ToolRegistry not injected"):
            _ = agent.tool_registry

    def test_skill_registry_not_set(self, mock_llm_client):
        agent = TestAgent(mock_llm_client)
        with pytest.raises(RuntimeError, match="SkillRegistry not injected"):
            _ = agent.skill_registry

    def test_tool_registry_setter(self, mock_llm_client, tool_registry):
        agent = TestAgent(mock_llm_client)
        agent.tool_registry = tool_registry
        assert agent.tool_registry == tool_registry

    def test_skill_registry_setter(self, mock_llm_client, skill_registry):
        agent = TestAgent(mock_llm_client)
        agent.skill_registry = skill_registry
        assert agent.skill_registry == skill_registry

    def test_execute_returns_task_result(self, mock_llm_client):
        agent = TestAgent(mock_llm_client)
        task = Task(task_id="test_1", task_type="test")
        result = agent.execute(task)
        assert isinstance(result, TaskResult)
        assert result.success
        assert result.task_id == "test_1"
        assert result.agent_name == "test_agent"

    def test_build_messages(self, mock_llm_client):
        agent = TestAgent(mock_llm_client)
        messages = agent._build_messages("Hello")
        assert len(messages) == 2
        assert messages[0] == {"role": "system", "content": "You are a test agent."}
        assert messages[1] == {"role": "user", "content": "Hello"}

    def test_repr(self, mock_llm_client):
        agent = TestAgent(mock_llm_client)
        assert "TestAgent" in repr(agent)
        assert "test_agent" in repr(agent)
