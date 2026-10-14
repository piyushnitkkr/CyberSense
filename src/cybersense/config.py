"""Pydantic-settings configuration loaded from config.yaml + .env."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]  # repo root
_CONFIG_YAML = _ROOT / "config.yaml"


def _load_yaml() -> dict[str, Any]:
    if _CONFIG_YAML.exists():
        with _CONFIG_YAML.open() as f:
            return yaml.safe_load(f) or {}
    return {}


class EmbeddingConfig(BaseSettings):
    model: str = "BAAI/bge-small-en-v1.5"
    device: str = "cpu"
    batch_size: int = 64
    dimension: int = 384


class ChunkingConfig(BaseSettings):
    target_tokens: int = 512
    max_tokens: int = 800
    min_tokens: int = 50
    overlap_tokens: int = 64


class RetrievalConfig(BaseSettings):
    k_dense: int = 30
    k_sparse: int = 30
    k_fused: int = 30
    top_k_retrieve: int = 30
    top_k_final: int = 8
    relevance_threshold: float = 0.3
    max_chunks_per_doc: int = 3
    reranker_enabled: bool = True
    reranker_model: str = "BAAI/bge-reranker-base"


class GenerationConfig(BaseSettings):
    provider: str = "anthropic"
    model: str = "claude-3-5-haiku-20241022"
    temperature: float = 0.1
    max_tokens: int = 1024
    history_turns: int = 6
    general_knowledge_fallback: bool = False


class QdrantConfig(BaseSettings):
    collection: str = "cybersense"
    prefer_grpc: bool = False


class ApiConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    upload_max_mb: int = 25
    allowed_extensions: list[str] = [".pdf", ".docx", ".md", ".txt", ".html"]
    rate_limit: str = "60/minute"


class IngestionConfig(BaseSettings):
    nvd_lookback_days: int = 730
    request_delay_seconds: float = 0.6
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    app_name: str = Field(default="CyberSense", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(default="sqlite+aiosqlite:///data/cybersense.db", alias="DATABASE_URL")

    # Secrets (from .env only)
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    nvd_api_key: str = Field(default="", alias="NVD_API_KEY")
    api_key: str = Field(default="", alias="API_KEY")
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=False, alias="DEBUG")

    # Sub-configs loaded from YAML then overridable
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)

    @classmethod
    def from_yaml_and_env(cls) -> "Settings":
        raw = _load_yaml()
        kwargs: dict[str, Any] = {}
        if "embedding" in raw:
            kwargs["embedding"] = EmbeddingConfig(**raw["embedding"])
        if "chunking" in raw:
            kwargs["chunking"] = ChunkingConfig(**raw["chunking"])
        if "retrieval" in raw:
            kwargs["retrieval"] = RetrievalConfig(**raw["retrieval"])
        if "generation" in raw:
            kwargs["generation"] = GenerationConfig(**raw["generation"])
        if "qdrant" in raw:
            kwargs["qdrant"] = QdrantConfig(**raw["qdrant"])
        if "api" in raw:
            kwargs["api"] = ApiConfig(**raw["api"])
        if "ingestion" in raw:
            kwargs["ingestion"] = IngestionConfig(**raw["ingestion"])
        return cls(**kwargs)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached)."""
    return Settings.from_yaml_and_env()
