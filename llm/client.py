"""
LLM client abstraction layer — multi-provider support (v0.4).

Supports: DeepSeek, OpenAI, Anthropic, Ollama, and any OpenAI-compatible API.
Unified interface via LLMClient with provider auto-detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generator


@dataclass
class LLMConfig:
    """LLM client configuration with multi-provider support.

    Attributes:
        provider: "deepseek" | "openai" | "anthropic" | "ollama" | "openai_compatible"
        api_key: API key for the provider.
        base_url: API base URL (optional, derived from provider if omitted).
        model: Model name (e.g. "deepseek-chat", "gpt-4o", "claude-sonnet-5").
        temperature: Generation temperature (0-2).
        max_tokens: Max tokens to generate.
        extra: Provider-specific extra params (e.g., top_k for Anthropic).
    """

    provider: str = "deepseek"
    api_key: str = ""
    base_url: str = ""
    model: str = "deepseek-chat"
    temperature: float = 0.8
    max_tokens: int = 4096
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Auto-derive base_url from provider if not set
        if not self.base_url:
            self.base_url = _DEFAULT_BASE_URLS.get(self.provider, "")

        # Auto-derive model from provider if using default
        if self.model == "deepseek-chat" and self.provider != "deepseek":
            self.model = _DEFAULT_MODELS.get(self.provider, self.model)


_DEFAULT_BASE_URLS: dict[str, str] = {
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
    "ollama": "http://localhost:11434/v1",
    "openai_compatible": "",
}

_DEFAULT_MODELS: dict[str, str] = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-5",
    "ollama": "llama3",
}


class LLMClient:
    """Multi-provider LLM client.

    Auto-selects the right SDK based on LLMConfig.provider:
      - deepseek/openai/ollama/openai_compatible → OpenAI SDK
      - anthropic → Anthropic SDK
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._provider = config.provider
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        if self._provider == "anthropic":
            self._init_anthropic()
        else:
            self._init_openai_compatible()

    def _init_openai_compatible(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

    def _init_anthropic(self) -> None:
        try:
            import anthropic
        except ImportError:
            raise ImportError("Anthropic SDK not installed. Run: pip install anthropic")
        self._client = anthropic.Anthropic(api_key=self.config.api_key)

    def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> str:
        """Send a chat completion request and return the response text."""
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        if self._provider == "anthropic":
            return self._chat_anthropic(messages, temp, max_tok, stop)
        return self._chat_openai(messages, temp, max_tok, stop)

    def _chat_openai(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        stop: list[str] | None,
    ) -> str:
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
        )
        return response.choices[0].message.content or ""

    def _chat_anthropic(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        stop: list[str] | None,
    ) -> str:
        system = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                user_messages.append(m)

        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system
        if stop:
            kwargs["stop_sequences"] = stop
        if temperature > 0:
            kwargs["temperature"] = temperature

        response = self._client.messages.create(**kwargs)
        first = response.content[0] if response.content else None
        if first and hasattr(first, "text"):
            return first.text
        return ""

    def chat_stream(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """Send a streaming chat completion request."""
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        if self._provider == "anthropic":
            yield from self._chat_stream_anthropic(messages, temp, max_tok)
        else:
            yield from self._chat_stream_openai(messages, temp, max_tok)

    def _chat_stream_openai(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> Generator[str, None, None]:
        stream = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _chat_stream_anthropic(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> Generator[str, None, None]:
        system = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                user_messages.append(m)

        kwargs: dict = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system
        if temperature > 0:
            kwargs["temperature"] = temperature

        with self._client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    # ── Async variants ────────────────────────────────────────

    async def achat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> str:
        """Async variant of chat()."""
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        if self._provider == "anthropic":
            return await self._achat_anthropic(messages, temp, max_tok, stop)
        return await self._achat_openai(messages, temp, max_tok, stop)

    async def _achat_openai(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        stop: list[str] | None,
    ) -> str:
        import asyncio

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
            ),
        )
        return response.choices[0].message.content or ""

    async def _achat_anthropic(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        stop: list[str] | None,
    ) -> str:
        import asyncio

        loop = asyncio.get_running_loop()
        system = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                user_messages.append(m)

        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system
        if stop:
            kwargs["stop_sequences"] = stop
        if temperature > 0:
            kwargs["temperature"] = temperature

        response = await loop.run_in_executor(
            None,
            lambda: self._client.messages.create(**kwargs),
        )
        first = response.content[0] if response.content else None
        if first and hasattr(first, "text"):
            return first.text
        return ""

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_choice: str = "auto",
        temperature: float | None = None,
    ) -> dict:
        """Send a chat completion with function/tool calling support.

        Returns the raw API response which may contain tool_calls.
        Note: Anthropic uses different tool format; this method currently
        delegates to the provider as-is (OpenAI format).
        """
        temp = temperature if temperature is not None else self.config.temperature
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temp,
        )
        return response.choices[0].message.model_dump()


def create_llm_client(
    provider: str = "deepseek",
    api_key: str = "",
    model: str = "",
    base_url: str = "",
    **kwargs,
) -> LLMClient:
    """Factory function: create an LLM client for any supported provider.

    Args:
        provider: "deepseek" | "openai" | "anthropic" | "ollama" | "openai_compatible"
        api_key: API key (required for most providers).
        model: Model name override (auto-derived from provider if omitted).
        base_url: API base URL override (auto-derived from provider if omitted).
        **kwargs: Additional LLMConfig fields (temperature, max_tokens, extra).

    Examples:
        # DeepSeek
        client = create_llm_client("deepseek", api_key="sk-...")

        # OpenAI
        client = create_llm_client("openai", api_key="sk-...", model="gpt-4o")

        # Anthropic
        client = create_llm_client("anthropic", api_key="sk-ant-...")

        # Ollama (local)
        client = create_llm_client("ollama", model="llama3")
    """
    config = LLMConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=kwargs.pop("temperature", 0.8),
        max_tokens=kwargs.pop("max_tokens", 4096),
        extra=kwargs,
    )
    return LLMClient(config)
