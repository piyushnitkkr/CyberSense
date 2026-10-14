"""Chat routes — POST /chat, GET/DELETE /sessions/{id}, POST /feedback."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cybersense.api.deps import (
    get_bm25,
    get_embedder,
    get_llm,
    get_reranker,
    get_vector_store,
    verify_api_key,
)
from cybersense.config import Settings, get_settings
from cybersense.db.session import get_session
from cybersense.db.tables import Feedback, Message, Session
from cybersense.generation.citations import build_citations
from cybersense.generation.guardrails import check_input
from cybersense.generation.llm import LLMClient
from cybersense.generation.prompts import build_chat_prompt, no_context_response
from cybersense.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Citation,
    FeedbackRequest,
)
from cybersense.retrieval.embeddings import EmbeddingModel
from cybersense.retrieval.query import QueryPipeline
from cybersense.retrieval.reranker import Reranker
from cybersense.retrieval.sparse import BM25Index
from cybersense.retrieval.vector_store import VectorStore

router = APIRouter(tags=["chat"])


async def _get_or_create_session(session_id: str | None, db: AsyncSession) -> Session:
    if session_id:
        stmt = select(Session).where(Session.id == session_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing
    new_session = Session(id=session_id or str(uuid.uuid4()))
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session


async def _get_history(session_id: str, db: AsyncSession, max_turns: int) -> list[ChatMessage]:
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(max_turns * 2)
    )
    result = await db.execute(stmt)
    messages = list(reversed(result.scalars().all()))
    return [ChatMessage(role=m.role, content=m.content) for m in messages]


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    embedder: EmbeddingModel = Depends(get_embedder),
    vector_store: VectorStore = Depends(get_vector_store),
    bm25: BM25Index = Depends(get_bm25),
    reranker: Reranker | None = Depends(get_reranker),
    llm: LLMClient = Depends(get_llm),
):
    # Safety check
    refusal = check_input(req.message)
    if refusal:
        raise HTTPException(status_code=400, detail=refusal)

    # Session management
    session = await _get_or_create_session(req.session_id, db)
    history = await _get_history(session.id, db, settings.generation.history_turns)

    # Retrieval
    pipeline = QueryPipeline(
        vector_store=vector_store,
        bm25=bm25,
        embedder=embedder,
        settings=settings,
        reranker=reranker,
        llm=llm,
    )
    chunks, rewritten_query, latency_ms = await pipeline.run(
        query=req.message, history=history, filters=req.filters
    )

    # Generation
    if not chunks:
        answer_text = no_context_response()
        citations: list[Citation] = []
    else:
        system, user_msg = build_chat_prompt(req.message, chunks, history)
        if req.stream:
            return _stream_response(llm, system, user_msg, chunks, session.id, rewritten_query, latency_ms, db)
        answer_raw = await llm.generate(user_msg, system=system, max_tokens=settings.generation.max_tokens)
        answer_text, citations = build_citations(answer_raw, chunks)

    # Persist messages
    message_id = str(uuid.uuid4())
    db.add(Message(
        id=message_id,
        session_id=session.id,
        role="user",
        content=req.message,
        rewritten_query=rewritten_query,
        latency_ms_json=json.dumps(latency_ms),
    ))
    db.add(Message(
        id=str(uuid.uuid4()),
        session_id=session.id,
        role="assistant",
        content=answer_text,
        citations_json=json.dumps([c.model_dump() for c in citations]),
    ))
    await db.commit()

    return ChatResponse(
        message_id=message_id,
        session_id=session.id,
        answer=answer_text,
        citations=citations,
        rewritten_query=rewritten_query,
        latency_ms=latency_ms,
    )


def _stream_response(llm, system, user_msg, chunks, session_id, rewritten_query, latency_ms, db):
    """Return a StreamingResponse with SSE-formatted tokens."""

    async def _generate() -> AsyncIterator[str]:
        collected = []
        async for token in llm.stream(user_msg, system=system):
            collected.append(token)
            yield f"data: {json.dumps({'token': token})}\n\n"

        full_answer = "".join(collected)
        clean, citations = build_citations(full_answer, chunks)
        payload = {
            "done": True,
            "answer": clean,
            "citations": [c.model_dump() for c in citations],
            "session_id": session_id,
            "rewritten_query": rewritten_query,
            "latency_ms": latency_ms,
        }
        yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")


@router.get("/sessions/{session_id}", dependencies=[Depends(verify_api_key)])
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_session)):
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found")
    return [{"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]


@router.delete("/sessions/{session_id}", dependencies=[Depends(verify_api_key)])
async def delete_session(session_id: str, db: AsyncSession = Depends(get_session)):
    stmt = select(Session).where(Session.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()
    return {"deleted": session_id}


@router.post("/feedback", dependencies=[Depends(verify_api_key)])
async def submit_feedback(req: FeedbackRequest, db: AsyncSession = Depends(get_session)):
    db.add(Feedback(message_id=req.message_id, rating=req.rating, comment=req.comment))
    await db.commit()
    return {"status": "recorded"}
