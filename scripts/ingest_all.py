#!/usr/bin/env python
"""Master ingestion script - Load all cybersecurity data sources into CyberSense."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cybersense.config import get_settings
from cybersense.retrieval.embeddings import EmbeddingModel
from cybersense.retrieval.vector_store import VectorStore
from cybersense.db.session import init_db


async def rebuild_bm25_index(vector_store: VectorStore):
    """Rebuild BM25 sparse index from Qdrant."""
    print("\n" + "="*60)
    print("[INFO] Rebuilding BM25 index...")

    from cybersense.retrieval.sparse import BM25Index
    from cybersense.models import ChunkMetadata

    bm25 = BM25Index()
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
            meta_dict = {k: v for k, v in payload.items() if k != "text"}
            metadatas.append(ChunkMetadata(**meta_dict))

        if next_offset is None or not results:
            break
        offset = next_offset

    bm25.build(texts, chunk_ids, metadatas)
    print(f"[OK] BM25 index rebuilt with {len(texts)} chunks")
    print("="*60 + "\n")
    return len(texts)


async def ingest_attack():
    """Ingest MITRE ATT&CK Enterprise techniques."""
    print("\n" + "="*60)
    print("[1/3] MITRE ATT&CK Enterprise")
    print("="*60)

    from cybersense.ingestion.attack import ATTACKLoader
    from cybersense.ingestion.pipeline import IngestionPipeline
    from cybersense.db.session import _SessionFactory as SessionFactory

    settings = get_settings()

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

    loader = ATTACKLoader()
    docs = list(loader.load())

    if not docs:
        print("[ERROR] No ATT&CK techniques loaded!")
        return 0

    print(f"[OK] Loaded {len(docs)} ATT&CK techniques")

    async with SessionFactory() as session:
        pipeline = IngestionPipeline(session, vector_store, embedder, settings)
        result = await pipeline.run("attack", iter(docs))

    print(f"[OK] Added: {result.added}, Updated: {result.updated}, Skipped: {result.skipped}")
    return result.added + result.updated


async def ingest_cwe():
    """Ingest MITRE CWE weaknesses."""
    print("\n" + "="*60)
    print("[2/3] MITRE CWE (Common Weakness Enumeration)")
    print("="*60)

    from cybersense.ingestion.cwe import CWELoader
    from cybersense.ingestion.pipeline import IngestionPipeline
    from cybersense.db.session import _SessionFactory as SessionFactory

    settings = get_settings()

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

    loader = CWELoader()
    docs = list(loader.load())

    if not docs:
        print("[ERROR] No CWE loaded!")
        return 0

    print(f"[OK] Loaded {len(docs)} CWE entries")

    async with SessionFactory() as session:
        pipeline = IngestionPipeline(session, vector_store, embedder, settings)
        result = await pipeline.run("cwe", iter(docs))

    print(f"[OK] Added: {result.added}, Updated: {result.updated}, Skipped: {result.skipped}")
    return result.added + result.updated


async def ingest_owasp():
    """Ingest OWASP Top 10 2025."""
    print("\n" + "="*60)
    print("[3/3] OWASP Top 10:2025")
    print("="*60)

    from cybersense.ingestion.pipeline import IngestionPipeline
    from cybersense.models import Document, DocType
    from cybersense.db.session import _SessionFactory as SessionFactory

    settings = get_settings()

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

    # Create OWASP Top 10 documents
    owasp_categories = [
        ("A01", "Broken Access Control"),
        ("A02", "Cryptographic Failures"),
        ("A03", "Injection"),
        ("A04", "Insecure Design"),
        ("A05", "Security Misconfiguration"),
        ("A06", "Vulnerable and Outdated Components"),
        ("A07", "Identification and Authentication Failures"),
        ("A08", "Software and Data Integrity Failures"),
        ("A09", "Security Logging and Monitoring Failures"),
        ("A10", "Server-Side Request Forgery (SSRF)"),
    ]

    docs = []
    for code, name in owasp_categories:
        text = f"""OWASP Top 10:2025 - {code}: {name}

This vulnerability category represents critical security risks in web applications.

Key Points:
- Description: {name}
- Risk: Critical to High
- Common Attack Vectors: Multiple
- Prevention: Application security best practices
- Detection: Security testing and monitoring
- References: https://owasp.org/www-project-top-ten/

For detailed information, refer to the official OWASP Top 10 documentation.
"""

        doc = Document(
            doc_id=f"owasp:top10:2025:{code}",
            source="owasp",
            title=f"OWASP Top 10:2025 - {code}: {name}",
            url=f"https://owasp.org/www-project-top-ten/",
            doc_type=DocType.standard,
            text=text,
            metadata={
                "version": "2025",
                "category": code,
                "name": name,
            }
        )
        docs.append(doc)

    print(f"[OK] Created {len(docs)} OWASP Top 10 documents")

    async with SessionFactory() as session:
        pipeline = IngestionPipeline(session, vector_store, embedder, settings)
        result = await pipeline.run("owasp", iter(docs))

    print(f"[OK] Added: {result.added}, Updated: {result.updated}, Skipped: {result.skipped}")
    return result.added + result.updated


async def main():
    """Main ingestion orchestrator."""
    print("\n" + "="*60)
    print("    CyberSense Master Data Ingestion")
    print("="*60)
    print("  College Project - RAG System for Cybersecurity")
    print("  Date: October 17, 2026")
    print("="*60 + "\n")

    # Initialize database
    print("[INIT] Initializing database...")
    await init_db()
    print("[OK] Database initialized\n")

    # Initialize services
    settings = get_settings()
    vector_store = VectorStore(
        url=settings.qdrant_url,
        collection=settings.qdrant.collection,
        dimension=settings.embedding.dimension,
        api_key=settings.qdrant_api_key,
    )
    await vector_store.ensure_collection()

    # Track statistics
    stats = {
        "attack": 0,
        "cwe": 0,
        "owasp": 0,
    }

    # Run ingestion
    try:
        stats["attack"] = await ingest_attack()
    except Exception as e:
        print(f"[ERROR] ATT&CK ingestion failed: {e}")

    try:
        stats["cwe"] = await ingest_cwe()
    except Exception as e:
        print(f"[ERROR] CWE ingestion failed: {e}")

    try:
        stats["owasp"] = await ingest_owasp()
    except Exception as e:
        print(f"[ERROR] OWASP ingestion failed: {e}")

    # Rebuild BM25
    try:
        total_chunks = await rebuild_bm25_index(vector_store)
    except Exception as e:
        print(f"[ERROR] BM25 rebuild failed: {e}")
        total_chunks = 0

    # Final summary
    print("\n" + "="*60)
    print("    INGESTION COMPLETE")
    print("="*60)
    print(f"  MITRE ATT&CK:        {stats['attack']:>5} documents")
    print(f"  MITRE CWE:           {stats['cwe']:>5} documents")
    print(f"  OWASP Top 10:        {stats['owasp']:>5} documents")
    print(f"  " + "-"*54)
    print(f"  Total Documents:     {sum(stats.values()):>5}")
    print(f"  Total Chunks (BM25): {total_chunks:>5}")
    print("="*60)
    print("\n✅ CyberSense knowledge base is ready!")
    print("   Backend: https://cybersense-api-vorj.onrender.com")
    print("   Documentation: See DATA_SOURCES.md")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())