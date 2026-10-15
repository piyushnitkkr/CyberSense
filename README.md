# CyberSense 🛡️

**CyberSense** is an enterprise-grade Retrieval-Augmented Generation (RAG) assistant built specifically for cybersecurity engineering, incident response, and vulnerability analysis.

It synthesizes knowledge across authoritative cybersecurity repositories — including **MITRE ATT&CK® Enterprise**, **CWE™**, **CAPEC™**, **CISA KEV**, **NVD (NIST)**, **NIST SP 800-53 / 800-63B**, and **OWASP** — providing grounded, fact-checked answers with verified inline citations.

---

## Key Features

- **Grounded & Cited Answers**: Every answer is strictly grounded in the indexed corpus. In-text citation tags (e.g. `[1]`, `[2]`) map directly to source documents with deep links and excerpt snippets.
- **Strict Abstention**: Hallucination-resistant; when a query falls outside the indexed knowledge base, CyberSense explicitly responds with *"I couldn't find relevant information in the knowledge base"* instead of guessing.
- **Dual-Retriever Architecture**:
  - **Dense Vector Search**: 384-dimensional semantic embeddings via `all-MiniLM-L6-v2` in **Qdrant**.
  - **Sparse Lexical Search**: Token-exact BM25 inverted index with regex short-circuiting for exact security IDs (`CVE-*`, `CWE-*`, `T*`, `AC-*`).
  - **Reciprocal Rank Fusion (RRF)**: Merges dense and sparse candidates.
  - **Cross-Encoder Reranker**: `ms-marco-MiniLM-L-6-v2` delivers fine-grained contextual relevance.
- **Defensive Guardrails**:
  - Refuses prompts requesting functional exploit scripts, malware payloads, or automated attack steps.
  - Sanitizes retrieved context chunks against indirect prompt-injection attempts.
- **Enterprise Ready**:
  - FastAPI backend with SSE streaming, asynchronous database sessions, and slowapi rate limiting.
  - Streamlit UI with source filtering, expandable citation cards, and private document upload support.

---

## Architecture

```
User Query
    │
    ▼
[Safety Guardrails] ──(Refusal if Exploit/Malware)──► 400 Bad Request
    │
    ▼
[Query Pipeline] ──(Rewrite with Chat History + Extract Security IDs)
    │
    ├───► [Dense Vector Search] (Qdrant)  ──┐
    │                                       ├──► [Reciprocal Rank Fusion] ──► [Cross-Encoder Reranker]
    └───► [Sparse BM25 Search]              ──┘                                         │
                                                                                        ▼
                                                                             [LLM Prompt Assembly]
                                                                                        │
                                                                                        ▼
                                                                             [Claude / Ollama LLM]
                                                                                        │
                                                                                        ▼
                                                                             [Citation Validator]
                                                                                        │
                                                                                        ▼
                                                                             Cited Response + Metadata
```

---

## Quickstart

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- *(Optional for local dev)* Python 3.11+, Anthropic API key or local Ollama instance.

### 1. Launch with Docker Compose

```bash
# Clone the repository
git clone https://github.com/your-org/CyberSense.git
cd CyberSense

# Configure environment variables
cp .env.example .env
# Edit .env and supply your ANTHROPIC_API_KEY (or use Ollama / fake provider)

# Build and start all services (Qdrant, API, Streamlit UI)
docker compose up -d
```

Once running:
- **Streamlit Web UI**: [http://localhost:8501](http://localhost:8501)
- **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Qdrant Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

### 2. Ingest Cybersecurity Knowledge

To populate the vector database with primary cybersecurity sources:

```bash
# Ingest all standard sources (KEV, ATT&CK, CWE, OWASP, NVD, NIST)
docker compose exec api python scripts/ingest.py --source all

# Or ingest a specific source with a record limit:
docker compose exec api python scripts/ingest.py --source kev
docker compose exec api python scripts/ingest.py --source attack --limit 100
```

---

### 3. Local Development Setup

If running without Docker:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package in editable mode with development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Start the API server
uvicorn cybersense.api.main:app --reload --port 8000

# Start the Streamlit UI (in a separate terminal)
streamlit run src/cybersense/ui/app.py
```

---

## Configuration Reference

Key configuration options in `config.yaml` or overridden via environment variables:

| Setting | Env Variable | Default | Description |
|---|---|---|---|
| `app_env` | `APP_ENV` | `development` | Deployment environment (`development`, `production`, `test`) |
| `log_level` | `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `qdrant_url` | `QDRANT_URL` | `http://localhost:6333` | Connection URL for Qdrant vector database |
| `database_url` | `DATABASE_URL` | `sqlite+aiosqlite:///data/cybersense.db` | SQLAlchemy database URL for sessions and registry |
| `generation.provider` | `LLM_PROVIDER` | `groq` | LLM backend (`groq`, `anthropic`, `ollama`, or `fake`) |
| `generation.model` | `LLM_MODEL` | `llama-3.1-8b-instant` | Name of the generative model |
| `retrieval.top_k_retrieve` | `TOP_K_RETRIEVE` | `20` | Candidate chunks retrieved per retriever |
| `retrieval.top_k_rerank` | `TOP_K_RERANK` | `8` | Final top-ranked chunks passed to the LLM |
| `retrieval.relevance_threshold` | `RELEVANCE_THRESHOLD`| `0.35` | Minimum score required before abstaining |

---

## Evaluation Benchmark

CyberSense includes an automated evaluation harness with a **60-question golden set** covering:
- 20 Exact-ID Lookups (CVE, CWE, ATT&CK, NIST)
- 20 Conceptual / Explanatory questions
- 10 Multi-document comparisons
- 5 Multi-turn conversation follow-ups
- 5 Unanswerable questions (abstention test)

Run evaluation:
```bash
py scripts/run_eval.py --golden eval/golden_set.jsonl --api http://localhost:8000
```

Detailed metrics and ablation results are recorded in [docs/EVALUATION.md](docs/EVALUATION.md).

---

## Documentation & Decisions

- [System Architecture](docs/ARCHITECTURE.md)
- [Architecture Decision Records (ADRs)](docs/DECISIONS.md)
- [Evaluation & Benchmark Analysis](docs/EVALUATION.md)
- [Data Sources & Licensing](data/SOURCES.md)

---

## Responsible Use Notice & Disclaimer

> **IMPORTANT**: CyberSense is strictly intended for **defensive security analysis**, educational research, and infrastructure hardening. It must not be utilized for unauthorized penetration testing, exploiting unpatched systems, or malware development. Answers generated by the AI should be verified against official advisories before executing production system changes.

---

## License

This project is licensed under the Apache 2.0 License. Third-party data feeds are governed by their respective licenses as detailed in [data/SOURCES.md](data/SOURCES.md).
