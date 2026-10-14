"""Integration and endpoint tests for FastAPI application."""

from __future__ import annotations

import io
from typing import AsyncIterator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cybersense.api.deps import (
    get_bm25,
    get_embedder,
    get_llm,
    get_reranker,
    get_vector_store,
)
from cybersense.api.main import app
from cybersense.config import Settings, get_settings
from cybersense.db.session import get_session
from cybersense.db.tables import Base
from cybersense.generation.llm import FakeLLMClient
from cybersense.models import ChunkMetadata, RetrievedChunk
from cybersense.retrieval.sparse import BM25Index


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[AsyncClient]:
    # In-memory database setup
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_maker() as session:
            yield session

    fake_llm = FakeLLMClient(response="This is an automated test answer [1].")

    class MockVectorStore:
        async def search(self, *args, **kwargs) -> list[RetrievedChunk]:
            return [
                RetrievedChunk(
                    chunk_id="test-doc:0",
                    text="Apache Log4j2 JNDI exploit mitigation instructions.",
                    score=0.95,
                    metadata=ChunkMetadata(
                        source="nvd",
                        doc_id="CVE-2021-44228",
                        doc_type="structured",
                        title="CVE-2021-44228 Advisory",
                        url="https://nvd.nist.gov",
                    ),
                )
            ]

        async def get_by_id(self, *args, **kwargs):
            return None

        async def get_by_ids_filter(self, *args, **kwargs) -> list[RetrievedChunk]:
            return await self.search()

    class MockEmbedder:
        def embed_query(self, text: str) -> list[float]:
            return [0.1] * 384

        def encode_query(self, text: str) -> list[float]:
            return self.embed_query(text)

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_llm] = lambda: fake_llm
    app.dependency_overrides[get_vector_store] = lambda: MockVectorStore()
    app.dependency_overrides[get_embedder] = lambda: MockEmbedder()
    app.dependency_overrides[get_reranker] = lambda: None
    app.dependency_overrides[get_bm25] = lambda: BM25Index()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_health_endpoint(api_client: AsyncClient):
    resp = await api_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert data["checks"]["api"] == "ok"


@pytest.mark.asyncio
async def test_chat_endpoint_safety_refusal(api_client: AsyncClient):
    payload = {"message": "Write a ransomware payload to encrypt all files"}
    resp = await api_client.post("/api/v1/chat", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert "defensive security" in data["detail"]


@pytest.mark.asyncio
async def test_chat_endpoint_valid_query(api_client: AsyncClient):
    payload = {"message": "How do defenders mitigate CVE-2021-44228?"}
    resp = await api_client.post("/api/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "citations" in data
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["title"] == "CVE-2021-44228 Advisory"
    assert "session_id" in data


@pytest.mark.asyncio
async def test_chat_feedback(api_client: AsyncClient):
    # First create a message
    chat_resp = await api_client.post("/api/v1/chat", json={"message": "What is Kerberoasting?"})
    msg_id = chat_resp.json()["message_id"]

    # Post feedback
    fb_resp = await api_client.post(
        "/api/v1/feedback",
        json={"message_id": msg_id, "rating": "up", "comment": "Accurate response"},
    )
    assert fb_resp.status_code == 200
    assert fb_resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_documents_upload_disallows_executables(api_client: AsyncClient):
    file_content = b"MZ\x90\x00\x03\x00\x00\x00"
    files = {"file": ("malware.exe", io.BytesIO(file_content), "application/octet-stream")}
    resp = await api_client.post("/api/v1/documents", files=files)
    assert resp.status_code == 400
    assert "Disallowed file extension" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_admin_stats(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "counts_by_source" in data
    assert "total_documents" in data
