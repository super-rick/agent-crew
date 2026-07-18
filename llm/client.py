"""LLM client abstraction layer — OpenAI-compatible API wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generator

from openai import OpenAI


@dataclass
class LLMConfig:
    """LLM client configuration."""

    api_key: str
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"
    temperature: float = 0.8
    max_tokens: int = 4096


@dataclass
class ChatMessage:
    """A single chat message."""

    role: str  # "system" | "user" | "assistant"
    content: str


class LLMClient:
    """OpenAI-compatible API wrapper.

    Unified interface for DeepSeek, OpenAI, and any OpenAI-compatible API.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )

    def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> str:
        """Send a chat completion request and return the response text."""
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            stop=stop,
        )
        return response.choices[0].message.content or ""

    def chat_stream(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """Send a streaming chat completion request."""
        stream = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_choice: str = "auto",
        temperature: float | None = None,
    ) -> dict:
        """Send a chat completion with function/tool calling support.

        Returns the raw API response which may contain tool_calls.
        """
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature or self.config.temperature,
        )
        return response.choices[0].message.model_dump()
