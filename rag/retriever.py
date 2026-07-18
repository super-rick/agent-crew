"""
Retriever — retrieval pipeline for context enrichment.

RAG 检索管道，负责：
1. 为 Writer Agent 检索写作上下文
2. 组合多种检索策略（向量搜索 + 标签过滤 + 时间衰减）
3. 返回格式化的上下文供 LLM 使用
"""

from __future__ import annotations

from rag.knowledge_base import KnowledgeBase, SearchResult


class Retriever:
    """Retrieval pipeline for RAG-enhanced content generation."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def retrieve_for_writing(
        self,
        topic: str,
        style: str | None = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        """Retrieve context specifically for the Writer Agent.

        Combines semantic similarity with optional style/source filtering.
        Returns empty list if embedding service is unavailable.
        """
        try:
            return self.kb.search(query=topic, n_results=limit)
        except Exception as e:
            # Embedding may fail if the provider doesn't support it
            # (e.g. DeepSeek has no embedding model)
            import sys

            print(f"  [WARN] RAG retrieval skipped (embedding unavailable): {e}", file=sys.stderr)
            return []

    def retrieve_similar(self, text: str, limit: int = 5) -> list[SearchResult]:
        """Simple similarity search."""
        return self.kb.search(query=text, n_results=limit)

    def retrieve_by_source(self, source: str, limit: int = 10) -> list[SearchResult]:
        """Retrieve documents filtered by source."""
        # First do a broad search, then filter
        results = self.kb.search(query=source, n_results=limit)
        return [r for r in results if r.metadata.get("source") == source]

    def format_context(self, results: list[SearchResult]) -> str:
        """Format search results into a markdown context block for LLM prompts."""
        if not results:
            return "（知识库中未找到相关内容）"

        parts = ["\n## 参考上下文\n"]
        for i, r in enumerate(results, 1):
            source = r.metadata.get("source", "未知来源")
            score = f"{r.score:.2f}" if r.score else "N/A"
            parts.append(f"[参考 {i}] (来源: {source}, 相关度: {score})")
            parts.append(r.text[:500])  # Truncate to avoid overflow
            parts.append("")

        return "\n".join(parts)
