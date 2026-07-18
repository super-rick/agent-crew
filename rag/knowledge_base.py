from __future__ import annotations
"""
Knowledge Base — ChromaDB vector store wrapper.

知识库管理：文档入库、语义搜索、统计信息。
"""

from dataclasses import dataclass, field
from typing import Any

import chromadb
from chromadb.config import Settings

from rag.embedder import BaseEmbedder


@dataclass
class Document:
    """A document to be stored in the knowledge base."""

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    doc_id: str | None = None


@dataclass
class SearchResult:
    """Result of a knowledge base search."""

    text: str
    score: float
    metadata: dict[str, Any]


class KnowledgeBase:
    """Vector knowledge base — ChromaDB wrapper.

    Handles document ingestion, semantic search, and collection management.
    """

    def __init__(
        self,
        persist_dir: str,
        embedder: BaseEmbedder,
        collection_name: str = "agentcrew_mcn_kb",
    ):
        self.persist_dir = persist_dir
        self.embedder = embedder
        self.collection_name = collection_name

        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the knowledge base.

        Automatically generates embeddings via the configured embedder.
        """
        if not documents:
            return

        texts = [doc.text for doc in documents]
        ids = [
            doc.doc_id or f"doc_{hash(doc.text)}_{i}"
            for i, doc in enumerate(documents)
        ]
        metadatas = [doc.metadata for doc in documents]

        # Generate embeddings
        embeddings = self.embedder.embed(texts)

        # Determine which are new vs existing
        existing_ids = set()
        try:
            existing = self._collection.get(ids=ids, include=[])
            existing_ids = set(existing.get("ids", []))
        except Exception:
            pass

        new_ids, new_embeddings, new_texts, new_metadatas = [], [], [], []
        for i, doc_id in enumerate(ids):
            if doc_id in existing_ids:
                continue
            new_ids.append(doc_id)
            new_embeddings.append(embeddings[i])
            new_texts.append(texts[i])
            new_metadatas.append(metadatas[i] if metadatas else {})

        if new_ids:
            self._collection.add(
                ids=new_ids,
                embeddings=new_embeddings,
                documents=new_texts,
                metadatas=new_metadatas,
            )

    def add_texts(
        self,
        texts: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """Add raw texts (wrapped as Documents)."""
        documents = []
        for i, text in enumerate(texts):
            documents.append(
                Document(
                    text=text,
                    metadata=metadatas[i] if metadatas else {},
                    doc_id=ids[i] if ids else None,
                )
            )
        self.add_documents(documents)

    def search(self, query: str, n_results: int = 5, where: dict | None = None) -> list[SearchResult]:
        """Semantic search across the knowledge base."""
        query_embedding = self.embedder.embed_query(query)

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        search_results = []
        for i in range(len(results["ids"][0])):
            search_results.append(
                SearchResult(
                    text=results["documents"][0][i],
                    score=1.0 - results["distances"][0][i],  # Convert distance to similarity
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                )
            )

        return search_results

    def get_stats(self) -> dict:
        """Return knowledge base statistics."""
        try:
            count = self._collection.count()
        except Exception:
            count = 0
        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "persist_dir": self.persist_dir,
        }

    def delete_by_source(self, source: str) -> None:
        """Delete all documents with a specific source metadata value."""
        self._collection.delete(where={"source": source})
