#!/usr/bin/env python
"""Ingest MITRE ATT&CK Enterprise techniques into Qdrant."""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cybersense.config import get_settings
from cybersense.retrieval.embeddings import EmbeddingModel
from cybersense.retrieval.vector_store import VectorStore
from cybersense.ingestion.attack import ATTACKLoader
from cybersense.ingestion.pipeline import IngestionPipeline
from cybersense.db.session import _SessionFactory as SessionFactory


async def main():
    settings = get_settings()
    print(f"[INFO] Ingesting MITRE ATT&CK from GitHub...")
    print(f"  URL: https://github.com/mitre-attack/attack-stix-data")

    # Initialize services
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

    # Load ATT&CK data
    loader = ATTACKLoader()
    docs = list(loader.load())

    if not docs:
        print("[ERROR] No ATT&CK techniques loaded!")
        return

    print(f"[OK] Loaded {len(docs)} ATT&CK techniques")

    async with SessionFactory() as session:
        pipeline = IngestionPipeline(session, vector_store, embedder, settings)
        result = await pipeline.run("attack", iter(docs))

    print(f"[OK] Ingestion complete:")
    print(f"  Added: {result.added}")
    print(f"  Updated: {result.updated}")
    print(f"  Skipped: {result.skipped}")
    print(f"  Failed: {result.failed}")

    # Rebuild BM25 index
    print("\n[INFO] Rebuilding BM25 index...")
    from cybersense.api.deps import get_bm25
    bm25 = get_bm25()

    texts = []
    chunk_ids = []
    metadatas = []
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
        except Exception as e:
            print(f"[ERROR] BM25 rebuild failed: {e}")
            break

        for point in results:
            payload = point.payload or {}
            text = payload.get("text") or payload.get("title", "")
            texts.append(text)
            chunk_ids.append(str(point.id))
            from cybersense.models import ChunkMetadata
            meta_dict = {k: v for k, v in payload.items() if k != "text"}
            metadatas.append(ChunkMetadata(**meta_dict))

        if next_offset is None or not results:
            break
        offset = next_offset

    bm25.build(texts, chunk_ids, metadatas)
    print(f"[OK] BM25 index rebuilt with {len(texts)} chunks")


if __name__ == "__main__":
    asyncio.run(main())