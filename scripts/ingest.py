"""CLI: ingest one or more sources into CyberSense.

Usage:
    py scripts/ingest.py --source all
    py scripts/ingest.py --source attack --limit 50
    py scripts/ingest.py --source nvd --since 2024-01-01
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Make sure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cybersense.config import get_settings
from cybersense.db.session import init_db, get_session
from cybersense.ingestion.pipeline import IngestionPipeline
from cybersense.logging import setup_logging
from cybersense.retrieval.embeddings import EmbeddingModel
from cybersense.retrieval.vector_store import VectorStore
from cybersense.scripts_lib import SOURCES, get_loader_for_source


async def run(source: str, since: str | None, limit: int | None) -> None:
    settings = get_settings()
    setup_logging(level=settings.log_level)

    embedder = EmbeddingModel(
        model_name=settings.embedding.model,
        device=settings.embedding.device,
        batch_size=settings.embedding.batch_size,
    )
    vector_store = VectorStore(
        url=settings.qdrant_url,
        collection=settings.qdrant.collection,
        dimension=settings.embedding.dimension,
    )
    await init_db()
    await vector_store.ensure_collection()

    sources_to_run = SOURCES if source == "all" else [source]

    async for session in get_session():
        for src in sources_to_run:
            print(f"\n{'='*60}\nIngesting: {src}\n{'='*60}")
            try:
                loader = get_loader_for_source(src, settings)
                docs = loader.load(since=since, limit=limit)
                if limit:
                    import itertools
                    docs = itertools.islice(docs, limit)
                pipeline = IngestionPipeline(session, vector_store, embedder, settings)
                run_record = await pipeline.run(src, docs)
                print(
                    f"  seen={run_record.seen} added={run_record.added} "
                    f"updated={run_record.updated} skipped={run_record.skipped} "
                    f"failed={run_record.failed} status={run_record.status}"
                )
            except Exception as exc:
                print(f"  ERROR: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="CyberSense ingestion CLI")
    parser.add_argument("--source", required=True, help=f"Source to ingest: {['all'] + SOURCES}")
    parser.add_argument("--since", default=None, help="Only ingest items published after YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=None, help="Max documents to ingest per source")
    args = parser.parse_args()

    if args.source not in (["all"] + SOURCES):
        print(f"ERROR: unknown source {args.source!r}. Choose from: all, {', '.join(SOURCES)}")
        sys.exit(1)

    asyncio.run(run(args.source, args.since, args.limit))


if __name__ == "__main__":
    main()
