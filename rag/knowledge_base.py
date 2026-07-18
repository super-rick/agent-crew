"""
Knowledge Base — ChromaDB vector store wrapper.

知识库管理：文档入库、语义搜索、统计信息。
"""

from __future__ import annotations

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

    def add_documents(self, documents: list[Document], batch_size: int = 5) -> None:
        """Add documents to the knowledge base.

        Automatically generates embeddings via the configured embedder.
        Documents are processed in batches to avoid API payload limits and OOM.
        """
        if not documents:
            return

        texts = [doc.text for doc in documents]
        ids = [doc.doc_id or f"doc_{hash(doc.text)}_{i}" for i, doc in enumerate(documents)]
        metadatas = [doc.metadata for doc in documents]

        # Process in batches to avoid hitting embedding API limits
        for batch_start in range(0, len(documents), batch_size):
            batch_end = min(batch_start + batch_size, len(documents))
            batch_texts = texts[batch_start:batch_end]
            batch_ids = ids[batch_start:batch_end]
            batch_metadatas = metadatas[batch_start:batch_end]

            # Generate embeddings for this batch
            batch_embeddings = self.embedder.embed(batch_texts)

            # Determine which are new vs existing
            existing_ids = set()
            try:
                existing = self._collection.get(ids=batch_ids, include=[])
                existing_ids = set(existing.get("ids", []))
            except Exception:
                pass

            new_ids, new_embeddings, new_texts, new_metadatas = [], [], [], []
            for i, doc_id in enumerate(batch_ids):
                if doc_id in existing_ids:
                    continue
                new_ids.append(doc_id)
                new_embeddings.append(batch_embeddings[i])
                new_texts.append(batch_texts[i])
                new_metadatas.append(batch_metadatas[i] if batch_metadatas else {})

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
        batch_size: int = 5,
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
        self.add_documents(documents, batch_size=batch_size)

    def search(
        self, query: str, n_results: int = 5, where: dict | None = None
    ) -> list[SearchResult]:
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
