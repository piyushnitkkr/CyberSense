"""Query processing: entity extraction, rewriting, and the full retrieval pipeline."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

from cybersense.config import Settings
from cybersense.ingestion.enrich import extract_ids
from cybersense.logging import get_logger
from cybersense.models import ChatMessage, FilterParams, RetrievedChunk
from cybersense.retrieval.hybrid import reciprocal_rank_fusion

if TYPE_CHECKING:
    from cybersense.generation.llm import LLMClient
    from cybersense.retrieval.embeddings import EmbeddingModel
    from cybersense.retrieval.reranker import Reranker
    from cybersense.retrieval.sparse import BM25Index
    from cybersense.retrieval.vector_store import VectorStore

logger = get_logger(__name__)

_QUERY_REWRITE_PROMPT = """\
Given the following conversation history and a follow-up question in the cybersecurity domain, \
rewrite the question into a standalone query that captures all context.
Preserve important technical terms, acronyms, and domain-specific language.
Respond with ONLY the rewritten query (max 60 tokens). Do not explain.

History:
{history}

Follow-up: {question}
Standalone query:"""


class QueryPipeline:
    """Orchestrates query rewrite → entity extraction → hybrid retrieval → rerank."""

    def __init__(
        self,
        vector_store: "VectorStore",
        bm25: "BM25Index",
        embedder: "EmbeddingModel",
        settings: Settings,
        reranker: "Reranker | None" = None,
        llm: "LLMClient | None" = None,
    ) -> None:
        self.vector_store = vector_store
        self.bm25 = bm25
        self.embedder = embedder
        self.reranker = reranker
        self.llm = llm
        self.cfg = settings.retrieval

    async def run(
        self,
        query: str,
        history: list[ChatMessage] | None = None,
        filters: FilterParams | None = None,
    ) -> tuple[list[RetrievedChunk], str, dict[str, float]]:
        """Return (chunks, rewritten_query, latency_ms_dict)."""
        timings: dict[str, float] = {}
        history = history or []

        # 1. Query rewrite
        t0 = time.perf_counter()
        rewritten = await self._rewrite(query, history)
        timings["rewrite_ms"] = (time.perf_counter() - t0) * 1000

        # 2. Entity extraction — short-circuit for exact IDs (permanent knowledge only)
        t0 = time.perf_counter()
        entity_ids = extract_ids(rewritten)
        entity_chunks: list[RetrievedChunk] = []
        if entity_ids and hasattr(self.vector_store, "get_by_ids_filter"):
            entity_chunks = await self.vector_store.get_by_ids_filter(entity_ids, limit=20)
        timings["entity_ms"] = (time.perf_counter() - t0) * 1000

        # 3. Dense retrieval from permanent knowledge base (filter out session docs)
        t0 = time.perf_counter()
        filter_dict = self._build_filter_dict(filters)
        if filter_dict is None:
            filter_dict = {}

        # Add session filter if session_id is in history
        session_id = None
        for msg in history:
            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                # If we have session-aware messages, extract session_id
                pass

        # Remove session_id from filter_dict to search permanent knowledge only
        if "session_id" in filter_dict:
            del filter_dict["session_id"]

        if hasattr(self.embedder, "encode_query"):
            query_vec = self.embedder.encode_query(rewritten)
        elif hasattr(self.embedder, "embed_query"):
            query_vec = self.embedder.embed_query(rewritten)
        else:
            query_vec = self.embedder.encode([rewritten])[0]

        dense_chunks = await self.vector_store.search(
            query_vec, limit=self.cfg.k_dense, filters=filter_dict
        )
        timings["dense_ms"] = (time.perf_counter() - t0) * 1000

        # 4. Sparse (BM25) retrieval
        t0 = time.perf_counter()
        sparse_chunks = self.bm25.search(rewritten, k=self.cfg.k_sparse)
        timings["sparse_ms"] = (time.perf_counter() - t0) * 1000

        # 5. RRF fusion
        t0 = time.perf_counter()
        fused = reciprocal_rank_fusion(dense_chunks, sparse_chunks, top_n=self.cfg.k_fused)
        # Guarantee entity short-circuit chunks appear first
        if entity_chunks:
            seen_ids = {c.chunk_id for c in entity_chunks}
            fused = entity_chunks + [c for c in fused if c.chunk_id not in seen_ids]
        timings["fusion_ms"] = (time.perf_counter() - t0) * 1000

        # 6. Rerank (optional)
        t0 = time.perf_counter()
        if self.reranker and self.cfg.reranker_enabled:
            final = self.reranker.rerank(rewritten, fused, top_k=self.cfg.top_k_final)
        else:
            final = fused[: self.cfg.top_k_final]
        timings["rerank_ms"] = (time.perf_counter() - t0) * 1000

        # 7. Dedup and cap per-document
        final = self._dedup_and_cap(final, max_per_doc=self.cfg.max_chunks_per_doc)

        # 8. Relevance threshold check
        if final and final[0].score < self.cfg.relevance_threshold:
            logger.info("QueryPipeline: below relevance threshold, returning empty context")
            return [], rewritten, timings

        return final, rewritten, timings

    async def _rewrite(self, query: str, history: list[ChatMessage]) -> str:
        if not history or self.llm is None:
            return query
        history_str = "\n".join(f"{m.role}: {m.content}" for m in history[-4:])
        prompt = _QUERY_REWRITE_PROMPT.format(history=history_str, question=query)
        try:
            rewritten = await self.llm.generate(prompt, max_tokens=60)
            return rewritten.strip() or query
        except Exception as exc:
            logger.warning("Query rewrite failed", extra={"error": str(exc)})
            return query

    @staticmethod
    def _build_filter_dict(filters: FilterParams | None) -> dict | None:
        if not filters:
            return None
        result = {}
        if filters.sources:
            result["sources"] = filters.sources
        if filters.doc_types:
            result["doc_types"] = [d.value for d in filters.doc_types]
        return result or None

    @staticmethod
    def _dedup_and_cap(chunks: list[RetrievedChunk], max_per_doc: int = 3) -> list[RetrievedChunk]:
        seen_texts: set[str] = set()
        per_doc: dict[str, int] = {}
        result: list[RetrievedChunk] = []
        for chunk in chunks:
            # Near-duplicate check (first 200 chars)
            sig = chunk.text[:200].strip()
            if sig in seen_texts:
                continue
            seen_texts.add(sig)
            # Per-document cap
            doc_id = chunk.metadata.doc_id
            if per_doc.get(doc_id, 0) >= max_per_doc:
                continue
            per_doc[doc_id] = per_doc.get(doc_id, 0) + 1
            result.append(chunk)
        return result
