"""Shared pytest fixtures for CyberSense tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cybersense.config import Settings
from cybersense.db.tables import Base
from cybersense.generation.llm import FakeLLMClient
from cybersense.models import RetrievedChunk


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient(response="This is a verified test response [1].")


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        qdrant_url="http://localhost:6333",
        embedding_dimension=384,
        top_k_retrieve=5,
        top_k_rerank=3,
        relevance_threshold=0.3,
        strict_grounding=True,
    )


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def sample_chunk() -> RetrievedChunk:
    from cybersense.models import ChunkMetadata

    meta = ChunkMetadata(
        source="nvd",
        doc_id="cve-2021-44228",
        doc_type="structured",
        title="CVE-2021-44228 Log4Shell",
        url="https://nvd.nist.gov/vuln/detail/CVE-2021-44228",
        ids=["CVE-2021-44228"],
        cvss=10.0,
    )
    return RetrievedChunk(
        chunk_id="chk-test-01",
        text="Apache Log4j2 versions 2.0-beta9 through 2.15.0 JNDI features do not protect against attacker controlled LDAP.",
        score=0.95,
        metadata=meta,
    )
