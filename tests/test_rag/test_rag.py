from __future__ import annotations
"""Tests for the RAG module."""

from unittest.mock import MagicMock, patch

from rag.embedder import OpenAIEmbedder, create_embedder
from rag.knowledge_base import KnowledgeBase, Document
from rag.retriever import Retriever


class TestEmbedder:
    """Test suite for embedder."""

    def test_openai_embedder_initialization(self):
        """OpenAIEmbedder accepts api_key, base_url, model."""
        embedder = OpenAIEmbedder(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="text-embedding-3-small",
        )
        assert embedder is not None
        assert embedder._model == "text-embedding-3-small"

    def test_create_embedder_factory_defaults(self):
        """create_embedder uses defaults for minimal config."""
        embedder = create_embedder({"api_key": "test-key"})
        assert isinstance(embedder, OpenAIEmbedder)
        assert embedder._model == "text-embedding-3-small"

    def test_create_embedder_custom_model(self):
        """create_embedder passes through custom model and base_url."""
        embedder = create_embedder({
            "provider": "openai",
            "api_key": "test-key",
            "model": "custom-model",
            "base_url": "https://custom.api.com/v1",
        })
        assert embedder._model == "custom-model"

    def test_create_embedder_unsupported_provider(self):
        """create_embedder raises for unknown provider."""
        import pytest
        with pytest.raises(ValueError, match="Unsupported embedding provider"):
            create_embedder({"provider": "unknown", "api_key": "k"})


class TestKnowledgeBase:
    """Test suite for KnowledgeBase (with mocked ChromaDB)."""

    @patch("chromadb.PersistentClient")
    def test_initialization(self, mock_chroma):
        embedder = MagicMock()
        kb = KnowledgeBase(
            persist_dir="/tmp/test_chroma",
            embedder=embedder,
            collection_name="test_kb",
        )
        assert kb.collection_name == "test_kb"
        assert kb.persist_dir == "/tmp/test_chroma"
        mock_chroma.assert_called_once()

    @patch("chromadb.PersistentClient")
    def test_get_stats_empty(self, mock_chroma):
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

        embedder = MagicMock()
        kb = KnowledgeBase("/tmp/test", embedder, "test")
        stats = kb.get_stats()
        assert stats["document_count"] == 0
        assert stats["collection_name"] == "test"

    @patch("chromadb.PersistentClient")
    def test_add_documents_batching(self, mock_chroma):
        """Verify add_documents batches embedding calls correctly.

        7 documents with batch_size=3 should call embed() 3 times
        (ceil(7/3) = 3 batches: sizes 3, 3, 1).
        """
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}  # No existing docs
        mock_collection.count.return_value = 0
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

        # Track embed calls and their batch sizes
        embed_calls = []

        def embed_side_effect(texts):
            embed_calls.append(len(texts))
            embed_dim = 4
            return [[0.1] * embed_dim for _ in texts]

        embedder = MagicMock()
        embedder.embed = MagicMock(side_effect=embed_side_effect)

        kb = KnowledgeBase("/tmp/test", embedder, "test")

        documents = [Document(text=f"doc_{i}", metadata={}) for i in range(7)]
        kb.add_documents(documents, batch_size=3)

        # embed() should have been called ceil(7/3) = 3 times
        assert embedder.embed.call_count == 3
        # Batch sizes should be: 3, 3, 1
        assert embed_calls == [3, 3, 1]

    @patch("chromadb.PersistentClient")
    def test_add_documents_empty_list(self, mock_chroma):
        """add_documents with empty list should not call embed()."""
        mock_collection = MagicMock()
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

        embedder = MagicMock()
        kb = KnowledgeBase("/tmp/test", embedder, "test")
        kb.add_documents([])

        embedder.embed.assert_not_called()


class TestRetriever:
    """Test suite for Retriever."""

    def test_initialization(self):
        kb = MagicMock()
        retriever = Retriever(kb)
        assert retriever.kb == kb

    def test_format_context_empty(self):
        retriever = Retriever(MagicMock())
        result = retriever.format_context([])
        assert "未找到" in result

    def test_format_context_with_results(self):
        from rag.knowledge_base import SearchResult
        kb = MagicMock()
        retriever = Retriever(kb)

        results = [
            SearchResult(text="Test content here", score=0.95, metadata={"source": "blog"}),
        ]
        result = retriever.format_context(results)
        assert "Test content" in result
        assert "blog" in result
