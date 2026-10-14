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
    return {"document_counts_by_source": counts}
