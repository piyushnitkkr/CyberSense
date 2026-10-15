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

## 4. Free Public Cloud Deployment

You can host CyberSense with a public URL completely **free of cost** using this stack:

| Component | Platform | Free Tier |
|---|---|---|
| **FastAPI Backend** | [Render.com](https://render.com) | Free Web Service (750 hrs/month) |
| **Streamlit Web UI** | [Streamlit Community Cloud](https://streamlit.io/cloud) | 100% Free, unlimited public apps |
| **Vector Database** | [Qdrant Cloud](https://cloud.qdrant.io) | Free 1GB forever cluster (no credit card required) |
| **LLM Inference** | [Groq Cloud](https://console.groq.com) | Free Tier (30 req/min for Llama 3.1 8B) |

### Step-by-Step Deployment:

#### 1. Setup Free Qdrant Cloud Vector Database
1. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io) and create a **Free Tier cluster**.
2. Copy your **Cluster URL** (e.g. `https://xxxxxx.us-east4-0.gcp.cloud.qdrant.io:6333`) and generate an **API Key**.
3. Migrate your local indexed vectors to Qdrant Cloud:
   ```bash
   set QDRANT_CLOUD_URL=https://YOUR-CLUSTER-URL:6333
   set QDRANT_CLOUD_KEY=your-qdrant-api-key
   python scripts/upload_to_qdrant_cloud.py
   ```

#### 2. Deploy FastAPI Backend on Render.com
1. Fork or push this repository to your GitHub account.
2. Sign in to [Render.com](https://render.com) with GitHub.
3. Click **New +** > **Blueprint**, connect your CyberSense repo, and select `render.yaml`.
4. Render will prompt you for 3 environment variables:
   - `GROQ_API_KEY`: Your Groq API key from [console.groq.com](https://console.groq.com)
   - `QDRANT_URL`: Your Qdrant Cloud cluster URL
   - `QDRANT_API_KEY`: Your Qdrant Cloud API key
5. Click **Apply**. Once deployed, Render gives you a public URL (e.g. `https://cybersense-api.onrender.com`).

#### 3. Deploy Streamlit Web UI on Streamlit Community Cloud
1. Sign in to [share.streamlit.io](https://share.streamlit.io/) with GitHub.
2. Click **New app**.
3. Select your repository: `username/CyberSense`, branch: `main`, main file path: `streamlit_app.py`.
4. In **Advanced settings** > **Secrets**, enter:
   ```toml
   API_BASE_URL = "https://your-render-app.onrender.com"
   ```
5. Click **Deploy!** Your chatbot is now live for the public.

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
