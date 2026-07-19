"""Tests for image generation tool (v0.4)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agents.tools import ToolRegistry
from agents.writer import WriterAgent


class TestImageGenerationTool:
    """Test the generate_image tool."""

    def test_tool_registered(self):
        """generate_image should be in BUILTIN_TOOLS."""
        from agents.tools import BUILTIN_TOOLS

        names = [t.name for t in BUILTIN_TOOLS]
        assert "generate_image" in names

    def test_tool_no_api_key(self):
        """Without API key, should return error dict."""
        from agents.tools import BUILTIN_TOOLS

        tool = next(t for t in BUILTIN_TOOLS if t.name == "generate_image")
        result = tool.execute(prompt="test", api_key="")
        assert "error" in result

    def test_tool_generates_image(self):
        """With mocked OpenAI, should return image data."""
        from agents.tools import BUILTIN_TOOLS

        tool = next(t for t in BUILTIN_TOOLS if t.name == "generate_image")

        with patch("openai.OpenAI") as mock_ai:
            mock_client = MagicMock()
            mock_img = MagicMock()
            mock_img.url = "https://example.com/img.png"
            mock_img.revised_prompt = "Revised test prompt"
            mock_client.images.generate.return_value.data = [mock_img]
            mock_ai.return_value = mock_client

            result = tool.execute(prompt="test prompt", api_key="sk-test")
            assert result["url"] == "https://example.com/img.png"
            assert result["model"] == "dall-e-3"

    def test_tool_different_sizes(self):
        """Size parameter should work for portrait/landscape."""
        from agents.tools import BUILTIN_TOOLS

        tool = next(t for t in BUILTIN_TOOLS if t.name == "generate_image")

        with patch("openai.OpenAI") as mock_ai:
            mock_client = MagicMock()
            mock_img = MagicMock()
            mock_img.url = "https://example.com/portrait.png"
            mock_client.images.generate.return_value.data = [mock_img]
            mock_ai.return_value = mock_client

            result = tool.execute(prompt="test", size="1024x1792", api_key="sk-test")
            assert result["size"] == "1024x1792"

    def test_tool_api_error(self):
        """API error should return error dict."""
        from agents.tools import BUILTIN_TOOLS

        tool = next(t for t in BUILTIN_TOOLS if t.name == "generate_image")

        with patch("openai.OpenAI") as mock_ai:
            mock_ai.return_value.images.generate.side_effect = Exception("Rate limited")
            result = tool.execute(prompt="test", api_key="sk-test")
            assert "error" in result
            assert "Rate limited" in result["error"]

    def test_tool_falls_back_to_env_var(self):
        """If no api_key arg, should check env."""
        from agents.tools import BUILTIN_TOOLS

        tool = next(t for t in BUILTIN_TOOLS if t.name == "generate_image")

        with patch("openai.OpenAI") as mock_ai:
            with patch("os.environ", {"OPENAI_API_KEY": "env-key"}):
                mock_client = MagicMock()
                mock_img = MagicMock()
                mock_img.url = "https://example.com/env.png"
                mock_client.images.generate.return_value.data = [mock_img]
                mock_ai.return_value = mock_client

                result = tool.execute(prompt="test")
                assert result["url"] == "https://example.com/env.png"


class TestWriterCoverImage:
    """Test WriterAgent cover image generation."""

    def test_generate_cover_image(self, mock_llm_client):
        """Writer.generate_cover_image should delegate to tool."""
        writer = WriterAgent(mock_llm_client)

        # Mock the tool execution
        original_execute = writer._tool_registry.execute
        writer._tool_registry.execute = MagicMock(
            return_value={
                "url": "https://example.com/cover.png",
                "revised_prompt": "A cover image",
                "model": "dall-e-3",
            }
        )

        result = writer.generate_cover_image("Python async programming", "technical")
        assert result["url"] == "https://example.com/cover.png"
        writer._tool_registry.execute = original_execute

    def test_generate_cover_image_no_tool(self, mock_llm_client):
        """Should return error if generate_image tool not registered."""
        writer = WriterAgent(mock_llm_client)
        # Don't register tools
        writer._tool_registry = ToolRegistry()
        result = writer.generate_cover_image("Topic")
        assert "error" in result

    def test_generate_cover_image_styles(self, mock_llm_client):
        """Different styles should produce different prompts."""
        writer = WriterAgent(mock_llm_client)
        calls = []

        def track_call(name, **kw):
            calls.append(kw.get("prompt", ""))

        writer._tool_registry.execute = MagicMock(
            side_effect=lambda name, **kw: track_call(name, **kw) or {"url": "x"}
        )

        writer.generate_cover_image("AI Agents", "casual")
        writer.generate_cover_image("AI Agents", "promotional")

        assert len(calls) == 2
        assert calls[0] != calls[1]  # Different style = different prompt
