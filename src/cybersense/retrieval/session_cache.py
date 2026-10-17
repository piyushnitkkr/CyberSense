"""Session-based document caching for temporary RAG without permanent storage."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from cybersense.logging import get_logger
from cybersense.models import Chunk, RetrievedChunk

if TYPE_CHECKING:
    from cybersense.retrieval.embeddings import EmbeddingModel
    from cybersense.retrieval.vector_store import VectorStore

logger = get_logger(__name__)


class SessionCache:
    """Manages session-scoped document chunks for temporary RAG.

    Each session has its own isolated set of chunks that are cleared when the session ends.
    This prevents polluting the permanent knowledge base with user uploads.
    """

    def __init__(self, vector_store: "VectorStore", embedder: "EmbeddingModel") -> None:
        self.vector_store = vector_store
        self.embedder = embedder
        # In-memory session tracking
        self._session_docs: dict[str, list[str]] = {}  # session_id -> [doc_ids]

    async def add_document_to_session(
        self,
        session_id: str,
        chunks: list[Chunk],
        doc_id: str | None = None,
    ) -> str:
        """Add document chunks to a session's temporary cache.

        Returns the doc_id for tracking.
        """
        # Generate session-scoped doc_id
        if not doc_id:
            doc_id = f"session:{session_id}:{hashlib.md5(session_id.encode()).hexdigest()[:8]}"

        # Embed chunks
        texts = [c.text for c in chunks]
        vectors = []

        # Ultra-small batches for memory safety
        for i in range(0, len(texts), 2):
            batch = texts[i:i + 2]
            batch_vectors = self.embedder.encode(batch)
            vectors.extend(batch_vectors)
            import gc
            gc.collect()

        # Store in Qdrant with session metadata
        for chunk in chunks:
            chunk.metadata.session_id = session_id  # Tag with session
            chunk.metadata.doc_id = doc_id

        await self.vector_store.upsert_chunks(doc_id, chunks, vectors)

        # Track in session
        if session_id not in self._session_docs:
            self._session_docs[session_id] = []
        self._session_docs[session_id].append(doc_id)

        logger.info(
            "Added document to session cache",
            extra={"session_id": session_id, "doc_id": doc_id, "chunks": len(chunks)},
        )

        return doc_id

    async def search_session(
        self,
        session_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Search only within a session's cached documents."""
        if session_id not in self._session_docs:
            return []

        # Get query embedding
        query_vec = self.embedder.encode_query(query)

        # Search with session filter
        chunks = await self.vector_store.search(
            query_vector=query_vec,
            limit=top_k,
            filters={"session_id": session_id},  # Only this session's docs
        )

        return chunks

    async def clear_session(self, session_id: str) -> int:
        """Remove all cached documents for a session.

        Returns the number of documents cleared.
        """
        if session_id not in self._session_docs:
            return 0

        doc_ids = self._session_docs[session_id]

        # Delete each document from Qdrant
        for doc_id in doc_ids:
            try:
                await self.vector_store.delete_document(doc_id)
            except Exception as exc:
                logger.warning(
                    "Failed to delete session doc",
                    extra={"doc_id": doc_id, "error": str(exc)},
                )

        # Clear from tracking
        count = len(self._session_docs[session_id])
        del self._session_docs[session_id]

        logger.info(
            "Cleared session cache",
            extra={"session_id": session_id, "docs_removed": count},
        )

        return count

    def get_session_doc_count(self, session_id: str) -> int:
        """Get the number of documents cached for a session."""
        return len(self._session_docs.get(session_id, []))
