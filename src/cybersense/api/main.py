"""FastAPI application entry point with lifespan startup/shutdown."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from cybersense.api.routes_admin import router as admin_router
from cybersense.api.routes_chat import router as chat_router
from cybersense.api.routes_ingest import router as ingest_router
from cybersense.config import get_settings
from cybersense.db.session import init_db
from cybersense.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(level=settings.log_level)
    logger.info("CyberSense API starting up")
    await init_db()
    import os
    # Skip expensive BM25 preload on cloud/production to avoid OOM (512 MB free tier).
    # Dense vector search via Qdrant still works. BM25 can be rebuilt on-demand via
    # POST /api/v1/admin/rebuild-index if extra RAM becomes available.
    if os.environ.get("APP_ENV", "development") != "production":
        try:
            from cybersense.api.deps import get_bm25, get_vector_store
            from cybersense.api.routes_admin import rebuild_bm25_index
            vs = get_vector_store(settings)
            bm25 = get_bm25()
            await rebuild_bm25_index(vs, bm25)
        except Exception as exc:
            logger.warning("Could not pre-populate BM25 index on startup", extra={"error": str(exc)})

    yield
    logger.info("CyberSense API shutting down")


limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="CyberSense API",
    description="Cybersecurity RAG Chatbot — source-cited answers from indexed security knowledge.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error("Unhandled exception: %s\n%s", exc, tb)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/test-groq", tags=["debug"])
async def test_groq():
    """Verify Groq API connectivity and key configuration."""
    settings = get_settings()
    key = settings.groq_api_key or ""
    key_preview = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else f"len={len(key)}"
    try:
        from cybersense.generation.llm import GroqClient
        client = GroqClient(api_key=key, model=settings.generation.model)
        answer = await client.generate("Say 'Groq is operational!' in 4 words.")
        return {
            "status": "ok",
            "provider": settings.generation.provider,
            "model": settings.generation.model,
            "key": key_preview,
            "response": answer,
        }
    except Exception as exc:
        import traceback
        return {
            "status": "error",
            "provider": settings.generation.provider,
            "key": key_preview,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }


@app.get("/", tags=["root"])
async def root() -> dict:
    """Root info endpoint."""
    return {
        "service": "CyberSense API",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
        "version": "0.1.0",
        "description": "Cybersecurity RAG Chatbot API with grounded inline citations",
    }


@app.get("/health", tags=["health"])
async def health() -> dict:
    """Liveness + dependency check."""
    settings = get_settings()
    checks: dict[str, str] = {"api": "ok"}

    try:
        from qdrant_client import AsyncQdrantClient
        if settings.qdrant_url.startswith("http://") or settings.qdrant_url.startswith("https://"):
            import re
            url = settings.qdrant_url
            if "cloud.qdrant.io" in url:
                url = re.sub(r":6333/?$", "", url)
            client = AsyncQdrantClient(
                url=url,
                api_key=settings.qdrant_api_key or None,
                prefer_grpc=False,
            )
        elif settings.qdrant_url == ":memory:":
            client = AsyncQdrantClient(location=":memory:")
        else:
            client = AsyncQdrantClient(path=settings.qdrant_url)
        await client.get_collections()
        await client.close()
        checks["qdrant"] = "ok"
    except Exception as exc:
        checks["qdrant"] = f"error: {exc}"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
