"""Pydantic domain models shared across ingestion, retrieval, and generation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Document types ────────────────────────────────────────────────────────────

class DocType(str, Enum):
    technique = "technique"
    weakness = "weakness"
    cve = "cve"
    kev = "kev"
    standard = "standard"
    guide = "guide"
    advisory = "advisory"
    upload = "upload"
    unknown = "unknown"


class Document(BaseModel):
    """Normalized document yielded by every loader."""

    doc_id: str
    source: str                          # e.g. "attack", "nvd", "owasp"
    title: str
    url: str = ""
    doc_type: DocType = DocType.unknown
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str = ""               # SHA-256; set by pipeline


class ChunkMetadata(BaseModel):
    """Payload stored alongside every vector in Qdrant."""

    source: str
    doc_id: str
    doc_type: str
    title: str
    section_path: str = ""
    url: str = ""
    page: int | None = None
    published_date: str | None = None
    modified_date: str | None = None
    ids: list[str] = Field(default_factory=list)  # CVE/CWE/ATT&CK IDs found
    severity: str | None = None
    cvss: float | None = None
    ingested_at: str = ""
    content_hash: str = ""
    session_id: str = ""  # Session-scoped caching (empty for permanent docs)


class Chunk(BaseModel):
    """Text chunk ready for embedding and indexing."""

    chunk_id: str                        # "{doc_id}:{index}"
    doc_id: str
    text: str
    index: int
    metadata: ChunkMetadata


# ── Retrieval ─────────────────────────────────────────────────────────────────

class RetrievedChunk(BaseModel):
    """A chunk returned from retrieval with its score."""

    chunk_id: str
    text: str
    score: float
    metadata: ChunkMetadata


# ── Generation ────────────────────────────────────────────────────────────────

class Citation(BaseModel):
    n: int
    title: str
    source: str
    section_path: str = ""
    url: str = ""
    page: int | None = None
    snippet: str = ""


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


# ── API request / response ────────────────────────────────────────────────────

class FilterParams(BaseModel):
    sources: list[str] | None = None
    doc_types: list[DocType] | None = None
    date_from: str | None = None
    date_to: str | None = None
    top_k: int | None = None


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    filters: FilterParams | None = None
    stream: bool = False


class ChatResponse(BaseModel):
    message_id: str
    session_id: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    rewritten_query: str | None = None
    latency_ms: dict[str, float] = Field(default_factory=dict)


class FeedbackRequest(BaseModel):
    message_id: str
    rating: str                 # "up" | "down"
    comment: str | None = None


class IngestRequest(BaseModel):
    source: str
    since: str | None = None    # YYYY-MM-DD
    limit: int | None = None


class DocumentListItem(BaseModel):
    doc_id: str
    source: str
    title: str
    url: str
    doc_type: str
    status: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class IngestionRunStatus(BaseModel):
    id: int
    source: str
    started_at: datetime
    finished_at: datetime | None
    seen: int
    added: int
    updated: int
    skipped: int
    failed: int
    status: str
    error: str | None
