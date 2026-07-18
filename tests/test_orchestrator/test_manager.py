"""Tests for the orchestrator."""

from __future__ import annotations

import pytest

from unittest.mock import MagicMock

from orchestrator.manager import Orchestrator, PipelineResult
from agents.base import Task
from agents.writer import WriterAgent
from agents.publisher import PublisherAgent


class TestOrchestrator:
    """Test suite for Orchestrator."""

    def test_initialization(self):
        orch = Orchestrator()
        assert len(orch.agents) == 0
        assert len(orch.task_history) == 0

    def test_register_agent(self, mock_llm_client):
        orch = Orchestrator()
        writer = WriterAgent(mock_llm_client)
        orch.register_agent(writer)
        assert "writer" in orch.agents

    def test_get_agent(self, mock_llm_client):
        orch = Orchestrator()
        writer = WriterAgent(mock_llm_client)
        orch.register_agent(writer)
        assert orch.get_agent("writer") == writer

    def test_get_agent_not_found(self):
        orch = Orchestrator()
        with pytest.raises(KeyError):
            orch.get_agent("nonexistent")

    def test_create_task(self):
        orch = Orchestrator()
        task = orch.create_task("write", {"topic": "Test"})
        assert task.task_type == "write"
        assert task.params["topic"] == "Test"
        assert task.status == "pending"
        assert len(task.task_id) == 8  # UUID first 8 chars

    def test_create_task_default_params(self):
        orch = Orchestrator()
        task = orch.create_task("publish")
        assert task.params == {}

    def test_pipeline_result_to_dict(self):
        result = PipelineResult(
            success=True,
            pipeline_id="test_123",
            task_type="write",
            duration_seconds=1.5,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["pipeline_id"] == "test_123"
        assert d["task_type"] == "write"
        assert d["duration_seconds"] == 1.5

    def test_repr(self, mock_llm_client):
        orch = Orchestrator()
        assert "agents=[]" in repr(orch)
        writer = WriterAgent(mock_llm_client)
        orch.register_agent(writer)
        assert "writer" in repr(orch)


class TestOrchestratorErrorPaths:
    """Error path tests for execute_pipeline."""

    def test_unknown_task_type(self, mock_llm_client):
        """Unknown task_type returns failed PipelineResult."""
        orch = Orchestrator()
        task = Task(task_id="err", task_type="nonexistent")
        result = orch.execute_pipeline(task)
        assert result.success is False
        assert "Unknown task_type" in result.error_message

    def test_missing_agent_for_write(self):
        """write without registered writer agent fails."""
        orch = Orchestrator()
        task = Task(task_id="w1", task_type="write", params={"topic": "test"})
        result = orch.execute_pipeline(task)
        assert result.success is False
        assert "writer" in result.error_message or "not registered" in result.error_message

    def test_missing_agent_for_publish(self):
        """publish without registered publisher agent fails."""
        orch = Orchestrator()
        task = Task(task_id="p1", task_type="publish")
        result = orch.execute_pipeline(task)
        assert result.success is False
        assert "publisher" in result.error_message or "not registered" in result.error_message

    def test_write_and_publish_with_writer_failure(self, mock_llm_client):
        """When writer fails, publisher is skipped."""
        writer = WriterAgent(mock_llm_client)
        publisher = PublisherAgent(mock_llm_client)

        # Make writer.execute return failure
        original_execute = writer.execute

        def failing_execute(task):
            result = original_execute(task)
            result.success = False
            result.data = {}  # Empty data — no content
            return result

        writer.execute = failing_execute

        orch = Orchestrator()
        orch.register_agent(writer)
        orch.register_agent(publisher)

        task = Task(task_id="wp1", task_type="write_and_publish", params={"topic": "test"})
        result = orch.execute_pipeline(task)

        assert result.success is False
        assert "writer" in result.results
        assert result.results["writer"].success is False
        assert "Skipped" in result.results["publisher"].error_message
