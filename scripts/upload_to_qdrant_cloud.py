"""
upload_to_qdrant_cloud.py — One-time migration script.

Reads vectors from local Qdrant (data/qdrant_db) and uploads them to
your Qdrant Cloud free cluster.

Usage:
    set QDRANT_CLOUD_URL=https://YOUR-ID.us-east4-0.gcp.cloud.qdrant.io
    set QDRANT_CLOUD_KEY=your-api-key
    python scripts/upload_to_qdrant_cloud.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

CLOUD_URL = os.environ.get("QDRANT_CLOUD_URL") or os.environ.get("QDRANT_URL", "")
CLOUD_KEY = os.environ.get("QDRANT_CLOUD_KEY") or os.environ.get("QDRANT_API_KEY", "")
LOCAL_PATH = "data/qdrant_db"
COLLECTION = "cybersense"
BATCH_SIZE = 100


async def migrate() -> None:
    if not CLOUD_URL or not CLOUD_KEY:
        print("ERROR: Set QDRANT_CLOUD_URL and QDRANT_CLOUD_KEY environment variables first.")
        sys.exit(1)

    print(f"Connecting to local Qdrant at {LOCAL_PATH!r} ...")
    local = AsyncQdrantClient(path=LOCAL_PATH)

    print(f"Connecting to Qdrant Cloud at {CLOUD_URL!r} ...")
    cloud = AsyncQdrantClient(url=CLOUD_URL, api_key=CLOUD_KEY)

    # Count local vectors
    local_count = await local.count(collection_name=COLLECTION)
    print(f"Local collection has {local_count.count} points.")

    # Ensure collection exists on cloud
    existing = [c.name for c in (await cloud.get_collections()).collections]
    if COLLECTION not in existing:
        # Get dimension from local
        info = await local.get_collection(COLLECTION)
        dim = info.config.params.vectors.size
        await cloud.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        print(f"Created collection '{COLLECTION}' on Qdrant Cloud (dim={dim}).")
    else:
        cloud_count = await cloud.count(collection_name=COLLECTION)
        print(f"Cloud collection already has {cloud_count.count} points.")
        if cloud_count.count >= local_count.count:
            print("Cloud is up to date — nothing to upload.")
            return

    # Scroll and upload in batches
    offset = None
    uploaded = 0
    while True:
        results, next_offset = await local.scroll(
            collection_name=COLLECTION,
            limit=BATCH_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        if not results:
            break

        points = [
            PointStruct(id=r.id, vector=r.vector, payload=r.payload or {})
            for r in results
        ]
        await cloud.upsert(collection_name=COLLECTION, points=points)
        uploaded += len(points)
        print(f"  Uploaded {uploaded}/{local_count.count} ...", end="\r")

        if next_offset is None:
            break
        offset = next_offset

    print(f"\nDone! {uploaded} vectors uploaded to Qdrant Cloud.")
    await local.close()
    await cloud.close()


if __name__ == "__main__":
    asyncio.run(migrate())
