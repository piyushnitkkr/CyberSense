"""Qdrant vector store wrapper — handles collection management and upserts."""

from __future__ import annotations

from typing import Any

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import Distance, PointStruct, VectorParams

from cybersense.logging import get_logger
from cybersense.models import Chunk, ChunkMetadata, RetrievedChunk

logger = get_logger(__name__)


class VectorStore:
    """Async wrapper around Qdrant for upsert and dense search."""

    def __init__(self, url: str, collection: str, dimension: int, api_key: str = "") -> None:
        self.url = url
        self.collection = collection
        self.dimension = dimension
        self._api_key = api_key
        self._client: AsyncQdrantClient | None = None

    @property
    def client(self) -> AsyncQdrantClient:
        if self._client is None:
            if self.url.startswith("http://") or self.url.startswith("https://"):
                url = self.url
                if "cloud.qdrant.io" in url:
                    import re
                    url = re.sub(r":6333/?$", "", url)
                self._client = AsyncQdrantClient(
                    url=url,
                    api_key=self._api_key or None,
                    prefer_grpc=False,
                )
            elif self.url == ":memory:":
                self._client = AsyncQdrantClient(location=":memory:")
            else:
                self._client = AsyncQdrantClient(path=self.url)
        return self._client

    async def ensure_collection(self) -> None:
        """Create collection if it doesn't already exist and ensure payload indexes."""
        existing = [c.name for c in (await self.client.get_collections()).collections]
        if self.collection not in existing:
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection", extra={"collection": self.collection})

        for field in ["ids", "source", "doc_id"]:
            try:
                await self.client.create_payload_index(
                    collection_name=self.collection,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            except Exception:
                pass

    async def upsert_chunks(
        self,
        doc_id: str,
        chunks: list[Chunk],
        vectors: list[list[float]],
    ) -> None:
        """Remove old chunks for doc_id then insert new ones."""
        # Delete existing chunks for this document
        await self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))]
                )
            ),
        )

        if not chunks:
            return

        points = [
            PointStruct(
                id=self._chunk_uuid(chunk.chunk_id),
                vector=vec,
                payload={**chunk.metadata.model_dump(), "text": chunk.text, "chunk_id": chunk.chunk_id},
            )
            for chunk, vec in zip(chunks, vectors)
        ]
        await self.client.upsert(collection_name=self.collection, points=points)
        logger.debug(
            "Upserted chunks", extra={"doc_id": doc_id, "count": len(points)}
        )

    async def search(
        self,
        query_vector: list[float],
        limit: int = 30,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Dense vector search; returns RetrievedChunk list."""
        qdrant_filter = self._build_filter(filters) if filters else None
        if hasattr(self.client, "search"):
            results = await self.client.search(
                collection_name=self.collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=qdrant_filter,
                with_payload=True,
            )
        else:
            resp = await self.client.query_points(
                collection_name=self.collection,
                query=query_vector,
                limit=limit,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            results = resp.points

        return [
            RetrievedChunk(
                chunk_id=r.payload.get("chunk_id", r.payload.get("doc_id", "") + ":" + str(r.id)),
                text=r.payload.get("text", ""),
                score=r.score,
                metadata=ChunkMetadata(**{k: v for k, v in r.payload.items() if k not in ("text", "chunk_id")}),
            )
            for r in results
        ]

    async def get_by_ids_filter(
        self,
        ids: list[str],
        limit: int = 20,
    ) -> list[RetrievedChunk]:
        """Metadata-filter search for exact cybersecurity IDs (CVE, CWE, etc.)."""
        results = await self.client.scroll(
            collection_name=self.collection,
            scroll_filter=models.Filter(
                should=[
                    models.FieldCondition(key="ids", match=models.MatchAny(any=ids))
                ]
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        chunks, _ = results
        return [
            RetrievedChunk(
                chunk_id=c.payload.get("chunk_id", str(c.id)),
                text=c.payload.get("text", ""),
                score=1.0,  # exact match
                metadata=ChunkMetadata(**{k: v for k, v in c.payload.items() if k not in ("text", "chunk_id")}),
            )
            for c in chunks
        ]

    async def delete_document(self, doc_id: str) -> None:
        await self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))]
                )
            ),
        )

    def _build_filter(self, filters: dict[str, Any]) -> models.Filter:
        conditions = []
        if sources := filters.get("sources"):
            conditions.append(
                models.FieldCondition(key="source", match=models.MatchAny(any=sources))
            )
        if doc_types := filters.get("doc_types"):
            conditions.append(
                models.FieldCondition(key="doc_type", match=models.MatchAny(any=doc_types))
            )
        return models.Filter(must=conditions) if conditions else models.Filter()

    @staticmethod
    def _chunk_uuid(chunk_id: str) -> str:
        """Convert a chunk_id string to a UUID-compatible hex string (Qdrant requirement)."""
        import hashlib, uuid
        h = hashlib.md5(chunk_id.encode()).hexdigest()
        return str(uuid.UUID(h))
