#!/usr/bin/env python
"""Test if BM25 index has data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Direct import to avoid FastAPI dependencies
from cybersense.retrieval.sparse import BM25Index

# Create fresh BM25 instance
bm25 = BM25Index()

# Check BM25 structure
print(f"BM25 Index Status:")
print(f"  Type: {type(bm25)}")

if hasattr(bm25, 'corpus'):
    print(f"  Documents indexed: {len(bm25.corpus)}")
    print(f"  Total chunks: {len(bm25.chunk_ids)}")
else:
    print("  BM25 instance doesn't have 'corpus' attribute")

# Try to search
try:
    results = bm25.search("access control policy", k=5)
    print(f"\nTest search 'access control policy': {len(results)} results")
    for i, chunk in enumerate(results, 1):
        print(f"  [{i}] {chunk.metadata.title[:50]}")
except Exception as e:
    print(f"\n❌ BM25 search failed: {e}")

# Check if empty
if len(bm25.corpus) == 0:
    print("\n⚠️  BM25 is EMPTY! Need to rebuild it.")
    print("   On local dev: curl -X POST http://localhost:8000/api/v1/admin/rebuild-index")
    print("   On Render: curl -X POST https://cybersense-api-vorj.onrender.com/api/v1/admin/rebuild-index")
