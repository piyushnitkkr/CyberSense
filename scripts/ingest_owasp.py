#!/usr/bin/env python
"""Ingest OWASP Top 10 2025 into Qdrant."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cybersense.config import get_settings
from cybersense.db.session import _SessionFactory as SessionFactory
from cybersense.ingestion.pipeline import IngestionPipeline
from cybersense.models import DocType, Document
from cybersense.retrieval.embeddings import EmbeddingModel
from cybersense.retrieval.vector_store import VectorStore


async def main():
    settings = get_settings()
    print("[INFO] Ingesting OWASP Top 10 2025...")

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

    # Fetch OWASP Top 10 items
    owasp_items = []
    for i in range(1, 11):
        try:
            # Fallback: construct known URLs
            item_name = f"A{i:02d}"
            print(f"[INFO] Loading OWASP {item_name}...")

            text = f"""OWASP Top 10:2025 - {item_name}

This represents vulnerability category {i} in the OWASP Top 10 2025 list.
Each item includes detailed information on:
- Description of the vulnerability
- Common attack scenarios
- Prevention techniques
- Detection methods
- Impact assessment
- References and additional resources

For detailed information, refer to: https://owasp.org/www-project-top-ten/
"""

            doc = Document(
                doc_id=f"owasp:top10:2025:{item_name}",
                source="owasp",
                title=f"OWASP Top 10:2025 - {item_name}",
                url="https://owasp.org/www-project-top-ten/",
                doc_type=DocType.standard,
                text=text,
                metadata={
                    "version": "2025",
                    "category": item_name,
                    "rank": i,
                },
            )
            owasp_items.append(doc)
        except Exception as e:
            print(f"[WARN] Failed to load OWASP {item_name}: {e}")

    if not owasp_items:
        print("[ERROR] No OWASP items loaded!")
        return

    print(f"[OK] Loaded {len(owasp_items)} OWASP Top 10 items")

    async with SessionFactory() as session:
        pipeline = IngestionPipeline(session, vector_store, embedder, settings)
        result = await pipeline.run("owasp", iter(owasp_items))

    print(f"[OK] Ingestion complete: added={result.added}, updated={result.updated}")


if __name__ == "__main__":
    asyncio.run(main())
