#!/usr/bin/env python
"""Test if documents are actually being stored in Qdrant."""

import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cybersense.config import get_settings
from cybersense.retrieval.embeddings import EmbeddingModel
from cybersense.retrieval.vector_store import VectorStore
from cybersense.models import Document, DocType
from cybersense.ingestion.pipeline import IngestionPipeline
from cybersense.db.session import AsyncSessionLocal


async def test_ingestion():
    print("=" * 60)
    print("CYBERSENSE INGESTION + RETRIEVAL TEST")
    print("=" * 60)

    settings = get_settings()
    print(f"\n📋 Configuration:")
    print(f"   Qdrant URL: {settings.qdrant_url}")
    print(f"   Collection: {settings.qdrant.collection}")
    print(f"   Embedding model: {settings.embedding.model}")

    # Test 1: Can we connect to Qdrant?
    print("\n🔌 Test 1: Qdrant Connection")
    try:
        vector_store = VectorStore(
            url=settings.qdrant_url,
            collection=settings.qdrant.collection,
            dimension=settings.embedding.dimension,
            api_key=settings.qdrant_api_key,
        )
        await vector_store.ensure_collection()
        print("   ✅ Qdrant connected!")
    except Exception as e:
        print(f"   ❌ Qdrant connection failed: {e}")
        return

    # Test 2: Count existing chunks
    print("\n📊 Test 2: Check Existing Data")
    try:
        info = await vector_store.client.get_collection(settings.qdrant.collection)
        count = info.points_count
        print(f"   ℹ️  Total chunks in DB: {count}")
    except Exception as e:
        print(f"   ❌ Failed to get collection info: {e}")

    # Test 3: Create and ingest a test document
    print("\n📝 Test 3: Ingest Test Document")
    test_doc = Document(
        doc_id="test:policy001",
        source="test",
        title="Test Cybersecurity Policy",
        doc_type=DocType.guide,
        text="""Access Control Policy - AC-1: The organization shall develop, document, and disseminate an access control policy.
Account Management - AC-2: The organization shall manage information system accounts including establishing, activating, modifying, and removing accounts.
Incident Response - IR-4: The organization shall implement incident handling capability including preparation, detection, containment, and recovery.""",
        content_hash="",
    )
    test_doc.content_hash = hashlib.sha256(test_doc.text.encode()).hexdigest()

    print(f"   Doc ID: {test_doc.doc_id}")
    print(f"   Text length: {len(test_doc.text)} chars")

    # Get embedder
    print("\n🔢 Test 4: Embedding Model")
    try:
        embedder = EmbeddingModel(
            model_name=settings.embedding.model,
            device=settings.embedding.device,
            batch_size=settings.embedding.batch_size,
        )
        # Test encoding
        test_vec = embedder.encode(["test"])
        print(f"   ✅ Embedding model works! Vector dimension: {len(test_vec[0])}")
    except Exception as e:
        print(f"   ❌ Embedding model failed: {e}")
        return

    # Test 5: Perform ingestion
    print("\n💾 Test 5: Ingest into Qdrant")
    try:
        async with AsyncSessionLocal() as session:
            pipeline = IngestionPipeline(session, vector_store, embedder, settings)
            result = await pipeline.run("test", [test_doc])
            print(f"   ✅ Ingestion result: {result.status}")
            print(f"      Seen: {result.seen}, Added: {result.added}, Updated: {result.updated}")
    except Exception as e:
        print(f"   ❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 6: Search for the document
    print("\n🔍 Test 6: Retrieval Test")
    try:
        query = "access control policy account management"
        query_vec = embedder.encode_query(query)
        results = await vector_store.search(query_vec, limit=5)

        if results:
            print(f"   ✅ Found {len(results)} chunks!")
            for i, chunk in enumerate(results, 1):
                print(f"   [{i}] Score: {chunk.score:.3f} | {chunk.metadata.title}")
                print(f"       {chunk.text[:80]}...")
        else:
            print("   ❌ No results found!")
    except Exception as e:
        print(f"   ❌ Search failed: {e}")

    # Test 7: Final count
    print("\n📈 Test 7: Final Data Count")
    try:
        info = await vector_store.client.get_collection(settings.qdrant.collection)
        count = info.points_count
        print(f"   ℹ️  Total chunks after test: {count}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nIf all tests passed, the system should work!")
    print("If any test failed, note the error message for debugging.")


if __name__ == "__main__":
    import sys
    import hashlib
    from cybersense.db.session import AsyncSessionLocal

    asyncio.run(test_ingestion())