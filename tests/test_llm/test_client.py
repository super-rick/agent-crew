"""Tests for llm/client.py — LLMClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from llm.client import LLMClient, LLMConfig


class TestLLMConfig:
    def test_defaults(self):
        cfg = LLMConfig(api_key="test-key")
        assert cfg.model == "deepseek-chat"
        assert cfg.temperature == 0.8
        assert cfg.max_tokens == 4096
        assert cfg.base_url == "https://api.deepseek.com/v1"

    def test_custom_values(self):
        cfg = LLMConfig(
            api_key="k",
            base_url="https://custom.api/v1",
            model="custom-model",
            temperature=0.5,
            max_tokens=2048,
        )
        assert cfg.model == "custom-model"
        assert cfg.temperature == 0.5
        assert cfg.max_tokens == 2048


class TestLLMClientChat:
    """chat() — standard completion."""

    @patch("llm.client.OpenAI")
    def test_chat_returns_content(self, mock_openai):
        """chat() returns the message content string."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Hello from LLM"
        mock_client.chat.completions.create.return_value.choices = [mock_choice]
        mock_openai.return_value = mock_client

        client = LLMClient(LLMConfig(api_key="test"))
        result = client.chat([{"role": "user", "content": "hi"}])

        assert result == "Hello from LLM"
        mock_client.chat.completions.create.assert_called_once()

    @patch("llm.client.OpenAI")
    def test_chat_passes_parameters(self, mock_openai):
        """chat() forwards temperature, max_tokens, stop."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        mock_client.chat.completions.create.return_value.choices = [mock_choice]
        mock_openai.return_value = mock_client

        client = LLMClient(LLMConfig(api_key="test"))
        client.chat(
            [{"role": "user", "content": "hi"}],
            temperature=0.2,
            max_tokens=100,
            stop=["END"],
        )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 100
        assert call_kwargs["stop"] == ["END"]

    @patch("llm.client.OpenAI")
    def test_chat_empty_content_returns_empty_string(self, mock_openai):
        """chat() handles None/empty content gracefully."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_client.chat.completions.create.return_value.choices = [mock_choice]
        mock_openai.return_value = mock_client

        client = LLMClient(LLMConfig(api_key="test"))
        result = client.chat([{"role": "user", "content": ""}])
        assert result == ""


class TestLLMClientChatWithTools:
    """chat_with_tools() — function calling."""

    @patch("llm.client.OpenAI")
    def test_returns_raw_response_dict(self, mock_openai):
        """chat_with_tools() returns the model_dump() of the message."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.model_dump.return_value = {"role": "assistant", "content": "using tools"}
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=mock_message),
        ]
        mock_openai.return_value = mock_client

        client = LLMClient(LLMConfig(api_key="test"))
        tools = [{"type": "function", "function": {"name": "search", "parameters": {}}}]
        result = client.chat_with_tools(
            [{"role": "user", "content": "search for X"}],
            tools=tools,
        )

        assert result == {"role": "assistant", "content": "using tools"}
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["tools"] == tools
        assert call_kwargs["tool_choice"] == "auto"

    @patch("llm.client.OpenAI")
    def test_custom_tool_choice(self, mock_openai):
        """tool_choice parameter is forwarded."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.model_dump.return_value = {"role": "assistant"}
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=mock_message),
        ]
        mock_openai.return_value = mock_client

        client = LLMClient(LLMConfig(api_key="test"))
        client.chat_with_tools(
            [{"role": "user", "content": "x"}],
            tools=[{"type": "function", "function": {"name": "f", "parameters": {}}}],
            tool_choice="required",
        )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["tool_choice"] == "required"


class TestLLMClientChatStream:
    """chat_stream() — streaming completion."""

    @patch("llm.client.OpenAI")
    def test_stream_yields_content_chunks(self, mock_openai):
        """chat_stream() yields content from each chunk."""
        mock_client = MagicMock()
        chunks = []
        for text in ["Hello", " ", "World"]:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = text
            chunks.append(chunk)
        mock_client.chat.completions.create.return_value = chunks
        mock_openai.return_value = mock_client

        client = LLMClient(LLMConfig(api_key="test"))
        result = list(client.chat_stream([{"role": "user", "content": "hi"}]))

        assert result == ["Hello", " ", "World"]

    @patch("llm.client.OpenAI")
    def test_stream_skips_none_content(self, mock_openai):
        """chat_stream() skips chunks with None content."""
        mock_client = MagicMock()
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = None
        mock_client.chat.completions.create.return_value = [chunk]
        mock_openai.return_value = mock_client

        client = LLMClient(LLMConfig(api_key="test"))
        result = list(client.chat_stream([{"role": "user", "content": "hi"}]))
        assert result == []
