# CyberSense Troubleshooting: Why Chat Isn't Returning Data

## Problem Summary
- ✅ PDF ingestion works (no OOM on Render)
- ❌ Chat doesn't retrieve data when user asks questions
- ❌ Likely cause: **Qdrant vector DB is empty or not being queried correctly**

## Root Causes to Check

### 1. **Qdrant Database is Empty**
**Symptom:** Upload a PDF, then ask a question → no results

**Diagnosis:**
```bash
.venv/Scripts/python scripts/test_retrieval.py
```

**Fix if empty:**
- Upload a document via Streamlit UI → `/api/v1/documents` POST
- Verify it ingested: Check backend logs for "Upserted chunks"
- Then ask a question in chat

### 2. **Retrieval Query Not Searching Qdrant**
**Current flow (check in `src/cybersense/api/routes_chat.py`):**
1. User asks question
2. QueryPipeline.run() called
3. Dense search → `vector_store.search(query_vec, ...)`
4. Sparse search → `bm25.search(query, ...)`
5. Results fused and returned to LLM

**If step 3-4 return empty:**
- Check if query embedding is valid
- Verify Qdrant connection (`QDRANT_URL`, `QDRANT_API_KEY`)
- Check Qdrant has data: `test_retrieval.py`

### 3. **BM25 Index Not Built**
BM25 is an in-memory index that needs to be populated from Qdrant.

**Reset BM25:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/rebuild-index \
  -H "X-API-Key: your-key"
```

Or on Render:
```bash
curl -X POST https://cybersense-api-vorj.onrender.com/api/v1/admin/rebuild-index \
  -H "X-API-Key: your-key"
```

## Step-by-Step Fix

### Step 1: Verify PDF Upload
1. Open Streamlit
2. Go to sidebar → "Upload Document"
3. Upload a PDF
4. Should show: "✅ Ingested successfully!"

### Step 2: Verify Data in Qdrant
Run diagnostic:
```bash
.venv/Scripts/python scripts/test_retrieval.py
```

Expected output:
```
✓ Connected to Qdrant
✓ Collection 'cybersense' has N chunks
✓ Retrieved 3 chunks:
  [1] Score: 0.823 | Doc: upload:abc123 | Title: My PDF
```

### Step 3: Rebuild BM25 Index
```bash
.venv/Scripts/python -c "
import asyncio
from cybersense.api.deps import get_vector_store, get_bm25
from cybersense.api.routes_admin import rebuild_bm25_index
from cybersense.config import get_settings

async def main():
    settings = get_settings()
    vs = get_vector_store(settings)
    bm25 = get_bm25()
    result = await rebuild_bm25_index(vs, bm25)
    print(result)

asyncio.run(main())
"
```

### Step 4: Test Chat
1. Open Streamlit
2. Type a question relevant to your uploaded PDF
3. Should see answer with citations

## Expected Behavior After Fix

**User workflow:**
1. Upload PDF → Ingested into Qdrant permanently
2. Ask question → Vector search finds relevant chunks
3. LLM answers based on those chunks with [1] [2] citations
4. Session ends → Data stays in Qdrant for future use

## Key Files

- **Ingestion:** `src/cybersense/ingestion/pipeline.py` (ultra-light chunking)
- **Retrieval:** `src/cybersense/retrieval/query.py` (hybrid search)
- **Chat:** `src/cybersense/api/routes_chat.py` (orchestration)
- **Vector DB:** `src/cybersense/retrieval/vector_store.py` (Qdrant wrapper)

## Environment Variables to Check

```bash
# Qdrant connection
QDRANT_URL=http://localhost:6333  # or Render URL
QDRANT_API_KEY=your-key-if-needed

# LLM
GROQ_API_KEY=your-groq-key

# Optional API key
API_KEY=your-api-key
```

## Memory-Safe Ingestion (Already Fixed)

Current limits on Render 512MB:
- Max 15 PDF pages processed
- Max 15KB text per page
- Max 3 chunks per document
- Embed in batches of 2
- Explicit garbage collection between batches

This keeps memory usage under 350MB total (well below 512MB limit).
