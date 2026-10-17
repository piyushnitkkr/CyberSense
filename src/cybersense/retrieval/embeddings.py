"""Dense embedding model wrapper — uses fastembed (ONNX) on server, sentence-transformers locally."""

from __future__ import annotations

from cybersense.logging import get_logger

logger = get_logger(__name__)


class EmbeddingModel:
    """Thin wrapper around fastembed (cloud/production) or sentence-transformers (local).

    fastembed uses ONNX runtime — no PyTorch needed, ~30 MB model download,
    fits comfortably within Render's 512 MB free-tier RAM.
    """

    def __init__(
        self, model_name: str = "BAAI/bge-small-en-v1.5", device: str = "cpu", batch_size: int = 16
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = None
        self._use_fastembed: bool | None = None  # determined lazily

    def _load(self):
        """Load the model, preferring fastembed then falling back to sentence-transformers."""
        if self._model is not None:
            return

        import os

        cache_dir = os.environ.get("FASTEMBED_CACHE_PATH")

        # Try fastembed first (lightweight ONNX, no torch)
        try:
            from fastembed import TextEmbedding

            logger.info(
                "Loading embedding model via fastembed (ONNX)",
                extra={"model": self.model_name, "cache_dir": cache_dir},
            )
            self._model = TextEmbedding(
                model_name=self.model_name,
                cache_dir=cache_dir,
                threads=1,
                enable_cpu_mem_arena=False,
            )
            self._use_fastembed = True
            logger.info("FastEmbed model initialized successfully")
            return
        except ImportError:
            logger.info("fastembed not installed, checking sentence-transformers")
        except Exception as fe_err:
            logger.warning("fastembed failed to initialize", extra={"error": str(fe_err)})

        # Fallback: sentence-transformers (requires torch)
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(
                "Loading embedding model via sentence-transformers",
                extra={"model": self.model_name},
            )
            self._model = SentenceTransformer(self.model_name, device=self.device)
            self._use_fastembed = False
        except Exception as st_err:
            logger.error("Failed to load any embedding model", extra={"st_error": str(st_err)})
            raise RuntimeError(f"Could not load embedding backend: {st_err}") from st_err

    def encode(self, texts: list[str], normalize: bool = True) -> list[list[float]]:
        """Return list of embedding vectors."""
        if not texts:
            return []
        self._load()
        if self._use_fastembed:
            batch_sz = max(1, min(self.batch_size, 8))
            embeddings = list(self._model.embed(texts, batch_size=batch_sz))
            return [e.tolist() for e in embeddings]
        else:
            vecs = self._model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=normalize,
                show_progress_bar=False,
            )
            return vecs.tolist()

    def encode_query(self, query: str) -> list[float]:
        """Encode a single query string."""
        self._load()
        if self._use_fastembed:
            # fastembed handles query prefix internally for BGE models
            result = list(self._model.query_embed(query))
            return result[0].tolist()
        else:
            # BGE models use a query prefix for better asymmetric retrieval
            prefixed = f"Represent this sentence for searching relevant passages: {query}"
            return self.encode([prefixed])[0]
