"""Idempotent ingestion pipeline: load → chunk → embed → upsert Qdrant + SQLite."""

from __future__ import annotations

import gc
import hashlib
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cybersense.config import Settings
from cybersense.db.tables import DocumentRecord, IngestionRun
from cybersense.ingestion.enrich import extract_ids
from cybersense.logging import get_logger
from cybersense.models import Chunk, ChunkMetadata, Document

if TYPE_CHECKING:
    from cybersense.retrieval.embeddings import EmbeddingModel
    from cybersense.retrieval.vector_store import VectorStore

logger = get_logger(__name__)


class IngestionPipeline:
    """Orchestrates load → chunk → embed → store for any loader."""

    def __init__(
        self,
        session: AsyncSession,
        vector_store: VectorStore,
        embedder: EmbeddingModel,
        settings: Settings,
    ) -> None:
        self.session = session
        self.vector_store = vector_store
        self.embedder = embedder

    async def run(self, source: str, documents) -> IngestionRun:
        """Process an iterable of Documents; returns the IngestionRun record."""
        run = IngestionRun(source=source, started_at=datetime.utcnow(), status="running")
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)

        seen = added = updated = skipped = failed = 0

        try:
            for doc in documents:
                seen += 1
                try:
                    result = await self._process_document(doc)
                    if result == "added":
                        added += 1
                    elif result == "updated":
                        updated += 1
                    else:
                        skipped += 1
                except Exception as exc:
                    failed += 1
                    logger.error(
                        "Pipeline: failed to process document",
                        extra={"doc_id": doc.doc_id, "error": str(exc)},
                    )

                if seen % 100 == 0:
                    logger.info(
                        "Pipeline: progress",
                        extra={
                            "source": source,
                            "seen": seen,
                            "added": added,
                            "updated": updated,
                            "skipped": skipped,
                            "failed": failed,
                        },
                    )

        except Exception as exc:
            run.status = "error"
            run.error = str(exc)
            raise
        finally:
            run.seen = seen
            run.added = added
            run.updated = updated
            run.skipped = skipped
            run.failed = failed
            run.finished_at = datetime.utcnow()
            if run.status == "running":
                run.status = "completed"
            await self.session.commit()

        logger.info(
            "Pipeline: completed",
            extra={
                "source": source,
                "seen": seen,
                "added": added,
                "updated": updated,
                "skipped": skipped,
                "failed": failed,
            },
        )
        return run

    async def _process_document(self, doc: Document) -> str:
        """Return 'added', 'updated', or 'skipped'."""
        # Compute hash if not already set
        if not doc.content_hash:
            doc.content_hash = hashlib.sha256(doc.text.encode()).hexdigest()

        # Check existing record
        stmt = select(DocumentRecord).where(DocumentRecord.doc_id == doc.doc_id)
        result = await self.session.execute(stmt)
        existing: DocumentRecord | None = result.scalar_one_or_none()

        if existing and existing.content_hash == doc.content_hash:
            return "skipped"

        # Ultra-lightweight chunking to prevent any memory issues
        try:
            chunks = self._ultra_light_chunk(doc)
        except Exception as exc:
            logger.error(
                "Failed to chunk document", extra={"doc_id": doc.doc_id, "error": str(exc)}
            )
            raise

        # Cap chunks aggressively for Render's 512MB limit
        MAX_CHUNKS = 10
        if len(chunks) > MAX_CHUNKS:
            logger.info(
                "Capping document chunks for memory safety",
                extra={"doc_id": doc.doc_id, "original": len(chunks), "capped": MAX_CHUNKS},
            )
            chunks = chunks[:MAX_CHUNKS]

        # Ultra-small batch embedding for safety
        texts = [c.text for c in chunks]
        if texts:
            vectors = []
            for i in range(0, len(texts), 2):  # Batch of 2
                batch = texts[i : i + 2]
                batch_vectors = self.embedder.encode(batch)
                vectors.extend(batch_vectors)
                gc.collect()
        else:
            vectors = []

        # Upsert into vector store (removes old chunks, inserts new)
        await self.vector_store.upsert_chunks(doc.doc_id, chunks, vectors)

        # Upsert SQLite record
        ingested_at = datetime.utcnow().isoformat()
        for chunk in chunks:
            chunk.metadata.ingested_at = ingested_at

        if existing:
            existing.content_hash = doc.content_hash
            existing.chunk_count = len(chunks)
            existing.updated_at = datetime.utcnow()
            existing.status = "indexed"
            action = "updated"
        else:
            self.session.add(
                DocumentRecord(
                    doc_id=doc.doc_id,
                    source=doc.source,
                    title=doc.title,
                    url=doc.url,
                    doc_type=doc.doc_type.value,
                    content_hash=doc.content_hash,
                    chunk_count=len(chunks),
                    status="indexed",
                )
            )
            action = "added"

        await self.session.commit()
        return action

    def _ultra_light_chunk(self, doc: Document) -> list[Chunk]:
        """Lightweight chunking: splits text into capped-size chunks."""

        text = doc.text
        if not text.strip():
            return []

        # Limit total text processed to prevent any memory issues
        max_text_length = 15000  # ~3750 tokens - very conservative
        if len(text) > max_text_length:
            text = text[:max_text_length] + "... [content truncated for memory safety]"
            logger.info(
                "PDF: text truncated for memory safety",
                extra={
                    "doc_id": doc.doc_id,
                    "original_length": len(doc.text),
                    "truncated": max_text_length,
                },
            )

        # Create minimal number of chunks
        chunk_size = 7500  # ~1875 tokens per chunk
        chunks = []
        idx = 0
        max_chunks = 3

        for i in range(0, min(len(text), max_chunks * chunk_size), chunk_size):
            if idx >= max_chunks:
                break

            chunk_text = text[i : i + chunk_size]
            if not chunk_text.strip():
                continue

            meta = ChunkMetadata(
                source=doc.source,
                doc_id=doc.doc_id,
                doc_type=doc.doc_type.value,
                title=doc.title,
                section_path=doc.metadata.get("section_path", ""),
                url=doc.url,
                page=doc.metadata.get("page"),
                published_date=doc.metadata.get("published_date"),
                modified_date=doc.metadata.get("modified_date"),
                ids=extract_ids(chunk_text),
                severity=doc.metadata.get("severity"),
                cvss=doc.metadata.get("cvss"),
                content_hash=doc.content_hash,
            )
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}:{idx}",
                    doc_id=doc.doc_id,
                    text=chunk_text,
                    index=idx,
                    metadata=meta,
                )
            )
            idx += 1

        # Ensure we have at least one chunk if there's text
        if not chunks and text.strip():
            meta = ChunkMetadata(
                source=doc.source,
                doc_id=doc.doc_id,
                doc_type=doc.doc_type.value,
                title=doc.title,
                section_path=doc.metadata.get("section_path", ""),
                url=doc.url,
                page=doc.metadata.get("page"),
                published_date=doc.metadata.get("published_date"),
                modified_date=doc.metadata.get("modified_date"),
                ids=extract_ids(text[:1000]),
                severity=doc.metadata.get("severity"),
                cvss=doc.metadata.get("cvss"),
                content_hash=doc.content_hash,
            )
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}:0",
                    doc_id=doc.doc_id,
                    text=text[:1000],
                    index=0,
                    metadata=meta,
                )
            )

        return chunks
