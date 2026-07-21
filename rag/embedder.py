"""
RAG Embedding — text-to-vector conversion interface.

OpenAI 兼容协议实现，通过 factory 函数支持多协议扩展。
支持 provider: openai (cloud) | local (free ONNX, no API key).
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from openai import OpenAI


class BaseEmbedder(ABC):
    """Abstract embedding interface — implement for new protocols."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Convert a list of texts to vectors."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Convert a single query text to a vector."""


class OpenAIEmbedder(BaseEmbedder):
    """Embedding via any OpenAI-compatible API.

    Works with:
    - OpenAI (api.openai.com) — text-embedding-3-small / text-embedding-ada-002
    - SiliconFlow (api.siliconflow.cn) — BAAI/bge-large-zh-v1.5
    - Any /v1/embeddings-compatible endpoint
    """

    def __init__(self, api_key: str, base_url: str, model: str):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._model, input=texts)
        # Sort by index to maintain order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [d.embedding for d in sorted_data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class ChromaDBEmbedder(BaseEmbedder):
    """Local embedding via ChromaDB's built-in ONNX model.

    Uses all-MiniLM-L6-v2 (384-dim) — free, offline, no API key needed.
    Ships with chromadb; no extra dependencies required.
    """

    def __init__(self, embedding_function):
        self._ef = embedding_function

    def embed(self, texts: list[str]) -> list[list[float]]:
        # ChromaDB's embedding function accepts str or list[str]
        result = self._ef(texts)
        if isinstance(result[0], list):
            return result
        # Single text returned a single list — wrap it
        return [result] if not isinstance(result[0], (list, tuple)) else list(result)

    def embed_query(self, text: str) -> list[float]:
        result = self._ef([text])
        if isinstance(result, list) and len(result) > 0:
            return list(result[0]) if isinstance(result[0], (list, tuple)) else list(result)
        return list(result)


def create_embedder(embedding_config: dict) -> BaseEmbedder:
    """Factory: create an embedder from configuration.

    Args:
        embedding_config: dict with keys:
            - provider: "openai" | "local" (free ONNX, no API key)
            - model: model name string (for openai provider)
            - api_key: API key (supports ${ENV_VAR} resolution)
            - base_url: API base URL

    Returns:
        An embedder instance matching the configured provider.

    Provider notes:
        openai  — any /v1/embeddings endpoint (OpenAI, SiliconFlow, etc.)
        local   — ChromaDB's DefaultEmbeddingFunction (all-MiniLM-L6-v2, ONNX)

    Extensibility:
        Add new provider branches here. Each branch creates its own embedder
        class (implementing BaseEmbedder). The rest of the RAG pipeline is
        protocol-agnostic.
    """
    provider = embedding_config.get("provider", "openai")
    api_key = embedding_config.get("api_key", "")
    base_url = embedding_config.get("base_url", "https://api.openai.com/v1")
    model = embedding_config.get("model", "text-embedding-3-small")

    # Resolve ${ENV_VAR} placeholders
    api_key = _resolve_env(api_key)

    # Fallback: if no embedding-specific API key, try the LLM key
    if not api_key:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")

    if provider == "openai":
        if not api_key:
            raise ValueError(
                "No embedding API key configured. Options:\n"
                "  1. Set EMBEDDING_API_KEY in .env (see .env.example)\n"
                "  2. Use provider: local in config.yaml (free, offline ONNX)\n"
                "  3. Set DEEPSEEK_API_KEY as fallback (limited — DeepSeek has no embedding model)"
            )
        return OpenAIEmbedder(api_key=api_key, base_url=base_url, model=model)

    if provider == "local":
        from chromadb.utils import embedding_functions

        return ChromaDBEmbedder(embedding_functions.DefaultEmbeddingFunction())

    # Future providers — add elif branches here:
    # elif provider == "grpc":
    #     from rag.embedder_grpc import GrpcEmbedder
    #     return GrpcEmbedder(endpoint=embedding_config["endpoint"])

    raise ValueError(f"Unsupported embedding provider: {provider}. " "Supported: openai, local")


def _resolve_env(value: str) -> str:
    """Resolve ${ENV_VAR} placeholders in a config value."""
    if not isinstance(value, str) or "${" not in value:
        return value
    import re

    def _replace(match):
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    return re.sub(r"\$\{([^}]+)\}", _replace, value)
