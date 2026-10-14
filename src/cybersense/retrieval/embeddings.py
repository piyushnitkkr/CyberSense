"""Dense embedding model wrapper using sentence-transformers."""

from __future__ import annotations

from functools import cached_property

import numpy as np
from sentence_transformers import SentenceTransformer

from cybersense.logging import get_logger

logger = get_logger(__name__)


class EmbeddingModel:
    """Thin wrapper around SentenceTransformer; lazy-loads on first use."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", device: str = "cpu", batch_size: int = 64) -> None:
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Loading embedding model", extra={"model": self.model_name})
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def encode(self, texts: list[str], normalize: bool = True) -> list[list[float]]:
        """Return list of embedding vectors."""
        if not texts:
            return []
        vecs = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )
        return vecs.tolist()

    def encode_query(self, query: str) -> list[float]:
        """Encode a single query string."""
        # BGE models use a query prefix for better asymmetric retrieval
        prefixed = f"Represent this sentence for searching relevant passages: {query}"
        return self.encode([prefixed])[0]
