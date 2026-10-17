"""BM25 sparse retrieval over the indexed corpus."""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from cybersense.logging import get_logger
from cybersense.models import ChunkMetadata, RetrievedChunk

logger = get_logger(__name__)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_\-\.]+", text.lower())


class BM25Index:
    """In-memory BM25 index over chunk texts."""

    def __init__(self) -> None:
        self._corpus: list[str] = []
        self._chunk_ids: list[str] = []
        self._metadatas: list[ChunkMetadata] = []
        self._bm25: BM25Okapi | None = None

    def build(
        self,
        texts: list[str],
        chunk_ids: list[str],
        metadatas: list[ChunkMetadata],
    ) -> None:
        """Build the BM25 index from the full corpus."""
        self._corpus = texts
        self._chunk_ids = chunk_ids
        self._metadatas = metadatas
        if not texts:
            self._bm25 = None
            logger.info("BM25: corpus is empty, awaiting document ingestion")
            return
        tokenized = [_tokenize(t) for t in texts]
        if not any(tokenized):
            self._bm25 = None
            logger.info(
                "BM25: corpus contains no searchable tokens, awaiting valid document ingestion"
            )
            return
        self._bm25 = BM25Okapi(tokenized)
        logger.info("BM25: built index", extra={"corpus_size": len(texts)})

    def search(self, query: str, k: int = 30) -> list[RetrievedChunk]:
        """Return top-k results by BM25 score."""
        if self._bm25 is None:
            logger.warning("BM25: index not built yet")
            return []

        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)

        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

        results = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue
            results.append(
                RetrievedChunk(
                    chunk_id=self._chunk_ids[idx],
                    text=self._corpus[idx],
                    score=float(scores[idx]),
                    metadata=self._metadatas[idx],
                )
            )
        return results
