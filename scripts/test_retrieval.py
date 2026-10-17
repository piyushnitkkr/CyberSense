#!/usr/bin/env python
"""Quick diagnostic to test if ingestion -> retrieval pipeline works."""

import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cybersense.config import get_settings
from cybersense.retrieval.embeddings import EmbeddingModel
from cybersense.retrieval.vector_store import VectorStore


async def main():
    settings = get_settings()

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

    # Check if collection has data
    try:
        collection_info = await vector_store.client.get_collection(settings.qdrant.collection)
        point_count = collection_info.points_count
        print(f"[OK] Connected to Qdrant")
        print(f"[OK] Collection '{settings.qdrant.collection}' has {point_count} chunks")

        if point_count == 0:
            print("\n[WARN] Vector DB is EMPTY! No chunks indexed.")
            print("   Upload a document first via Streamlit sidebar.")
            return

        # Try a test search
        print(f"\n[INFO] Testing retrieval with sample query...")
        test_query = "cybersecurity access control policy"
        query_vec = embedder.encode_query(test_query)

        results = await vector_store.search(query_vec, limit=5)

        if results:
            print(f"[OK] Retrieved {len(results)} chunks:")
            for i, chunk in enumerate(results, 1):
                print(f"  [{i}] Score: {chunk.score:.3f} | Doc: {chunk.metadata.doc_id} | Title: {chunk.metadata.title}")
                print(f"      Text: {chunk.text[:120]}...")
        else:
            print("[FAIL] No results retrieved even though DB has chunks!")
            print("   This suggests a search/filter issue.")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
