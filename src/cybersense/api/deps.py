"""Shared FastAPI dependencies — injects settings, DB, retrieval, generation."""

from __future__ import annotations

import functools

from fastapi import Depends, Header, HTTPException, status

from cybersense.config import Settings, get_settings
from cybersense.generation.llm import LLMClient, build_llm_client
from cybersense.retrieval.embeddings import EmbeddingModel
from cybersense.retrieval.reranker import Reranker
from cybersense.retrieval.sparse import BM25Index
from cybersense.retrieval.vector_store import VectorStore

# ── Singletons (module-level cache) ──────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _get_embedder(model: str, device: str, batch_size: int) -> EmbeddingModel:
    return EmbeddingModel(model_name=model, device=device, batch_size=batch_size)


@functools.lru_cache(maxsize=1)
def _get_vector_store(url: str, collection: str, dimension: int, api_key: str = "") -> VectorStore:
    return VectorStore(url=url, collection=collection, dimension=dimension, api_key=api_key)


@functools.lru_cache(maxsize=1)
def _get_reranker(model: str, device: str) -> Reranker:
    return Reranker(model_name=model, device=device)


@functools.lru_cache(maxsize=1)
def _get_llm(provider: str) -> LLMClient:
    settings = get_settings()
    return build_llm_client(provider, settings)


# BM25 is mutable (rebuilt on ingest) — not cached with lru_cache
_bm25_index = BM25Index()


def get_bm25() -> BM25Index:
    return _bm25_index


def get_embedder(settings: Settings = Depends(get_settings)) -> EmbeddingModel:
    e = settings.embedding
    return _get_embedder(e.model, e.device, e.batch_size)


def get_vector_store(settings: Settings = Depends(get_settings)) -> VectorStore:
    return _get_vector_store(
        settings.qdrant_url,
        settings.qdrant.collection,
        settings.embedding.dimension,
        settings.qdrant_api_key,
    )


def get_reranker(settings: Settings = Depends(get_settings)) -> Reranker | None:
    if not settings.retrieval.reranker_enabled:
        return None
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return None
    r = settings.retrieval
    return _get_reranker(r.reranker_model, settings.embedding.device)


def get_llm(settings: Settings = Depends(get_settings)) -> LLMClient:
    return _get_llm(settings.generation.provider)


def verify_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """If an API key is configured, require it on every request."""
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
