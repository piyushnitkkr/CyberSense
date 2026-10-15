"""SQLAlchemy async session factory."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cybersense.db.tables import Base

import os

_DEFAULT_DB_DIR = Path(__file__).resolve().parents[3] / "db"
_DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite+aiosqlite:///{_DEFAULT_DB_DIR / 'cybersense.db'}"

_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
_SessionFactory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:  # type: ignore[return]
    """Dependency-injection helper that yields an async DB session."""
    async with _SessionFactory() as session:
        yield session
