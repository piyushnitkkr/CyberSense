"""Admin routes — BM25 index rebuild, collection stats."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cybersense.api.deps import get_bm25, get_vector_store, verify_api_key
from cybersense.db.session import get_session
from cybersense.db.tables import DocumentRecord

router = APIRouter(tags=["admin"])


@router.get("/admin/stats", dependencies=[Depends(verify_api_key)])
async def stats(db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(DocumentRecord.source, func.count(DocumentRecord.doc_id).label("count"))
        .group_by(DocumentRecord.source)
    )
    counts = {row.source: row.count for row in result}
    total = sum(counts.values())
    return {
        "counts_by_source": counts,
        "document_counts_by_source": counts,
        "total_documents": total,
    }


@router.post("/admin/rebuild-index", dependencies=[Depends(verify_api_key)])
async def rebuild_bm25_index(
    vector_store=Depends(get_vector_store),
    bm25=Depends(get_bm25),
):
    """Rebuild the in-memory BM25 index from all chunks currently in Qdrant."""
    from cybersense.models import ChunkMetadata

    texts: list[str] = []
    chunk_ids: list[str] = []
    metadatas: list[ChunkMetadata] = []
    offset = None

    while True:
        try:
            results, next_offset = await vector_store.client.scroll(
                collection_name=vector_store.collection,
                limit=500,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("BM25 rebuild: scroll failed, stopping early", extra={"error": str(exc)})
            break

        for point in results:
            payload = point.payload or {}
            text = payload.get("text") or payload.get("title", "")
            texts.append(text)
            chunk_ids.append(str(point.id))
            meta_dict = {k: v for k, v in payload.items() if k != "text"}
            try:
                metadatas.append(ChunkMetadata(**meta_dict))
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "BM25 rebuild: skipping point with invalid payload",
                    extra={"point_id": str(point.id), "error": str(exc)},
                )
                # Pop the text/chunk_id we just appended to keep lists in sync
                texts.pop()
                chunk_ids.pop()

        if next_offset is None or not results:
            break
        offset = next_offset

    bm25.build(texts, chunk_ids, metadatas)
    return {"status": "ok", "indexed_chunks": len(texts)}
