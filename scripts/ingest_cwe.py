#!/usr/bin/env python
"""Ingest MITRE CWE (Common Weakness Enumeration) into Qdrant."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cybersense.config import get_settings
from cybersense.db.session import _SessionFactory as SessionFactory
from cybersense.ingestion.cwe import CWELoader
from cybersense.ingestion.pipeline import IngestionPipeline
from cybersense.retrieval.embeddings import EmbeddingModel
from cybersense.retrieval.vector_store import VectorStore


async def main():
    settings = get_settings()
    print("[INFO] Ingesting MITRE CWE...")

    embedder = EmbeddingModel(
        model_name=settings.embedding.model,
        device=settings.embedding.device,
        batch_size=settings.embedding.batch_size,
    )

    vector_store = VectorStore(
        url=settings.qdrant_url,
        collection=settings.qdrant.collection,
        dimension=settings.embedding.dimension,
        api_key=settings.qdrant_api_key,
    )
    await vector_store.ensure_collection()

    # Load CWE data
    loader = CWELoader()
    docs = list(loader.load())

    if not docs:
        print("[ERROR] No CWE loaded!")
        return

    print(f"[OK] Loaded {len(docs)} CWE entries")

    async with SessionFactory() as session:
        pipeline = IngestionPipeline(session, vector_store, embedder, settings)
        result = await pipeline.run("cwe", iter(docs))

    print(f"[OK] Ingestion complete: added={result.added}, updated={result.updated}")


if __name__ == "__main__":
    asyncio.run(main())
