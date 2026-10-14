"""Cross-encoder reranker using BGE reranker or any compatible model."""

from __future__ import annotations

from cybersense.logging import get_logger
from cybersense.models import RetrievedChunk

logger = get_logger(__name__)


class Reranker:
    """Cross-encoder reranker; lazy-loads model on first use."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base", device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            logger.info("Loading reranker model", extra={"model": self.model_name})
            self._model = CrossEncoder(self.model_name, device=self.device)
        return self._model

    def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int = 8) -> list[RetrievedChunk]:
        """Score each chunk against the query and return top_k."""
        if not chunks:
            return []

        pairs = [[query, chunk.text] for chunk in chunks]
        scores = self.model.predict(pairs).tolist()

        scored = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        return [
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                score=float(score),
                metadata=chunk.metadata,
            )
            for score, chunk in scored[:top_k]
        ]
