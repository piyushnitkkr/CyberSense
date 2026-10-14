# Architecture & Design Decision Records (ADRs)

This document records the architectural and technology decisions made during the design and implementation of CyberSense.

---

## ADR 01: Vector Database Selection — Qdrant
- **Decision**: Adopt Qdrant as the primary vector store (with local container or in-memory mode).
- **Rationale**:
  - Native support for payload-based filtering (filtering by `source`, `doc_type`, `date`).
  - High performance, lightweight Rust core with low operational overhead.
  - First-class Python async client (`AsyncQdrantClient`).
  - Self-hostable via Docker Compose with no cloud vendor lock-in.

---

## ADR 02: Hybrid Retrieval with Reciprocal Rank Fusion (RRF)
- **Decision**: Combine dense vector embeddings (`all-MiniLM-L6-v2`) with sparse BM25 token matching using RRF ($k=60$).
- **Rationale**:
  - Dense embeddings excel at conceptual queries ("how does Kerberoasting work?"), but frequently miss exact identifiers like `CVE-2023-34362` or `T1059.001`.
  - BM25 excels at exact keyword and identifier lookup.
  - RRF provides parameter-free, scale-invariant rank combination without requiring complex score normalization.

---

## ADR 03: Two-Tier Storage Architecture (Qdrant + SQLite)
- **Decision**: Use Qdrant for vector embeddings and search payloads, while maintaining SQLite via SQLAlchemy for session history, ingestion status, and document hash registries.
- **Rationale**:
  - Keeps chat sessions and ingestion state ACID-compliant and easily inspectable with standard tools.
  - Enables idempotent ingestion: document SHA-256 hashes are verified in SQLite before triggering vector re-embedding.

---

## ADR 04: Two Chunking Strategies (Prose vs Structured Records)
- **Decision**: Differentiate chunking logic between unstructured prose documents (NIST SPs, OWASP guides) and structured threat entities (ATT&CK, CWE, CVE, KEV).
- **Rationale**:
  - Unstructured documents require heading-aware markdown splitting and overlap to preserve narrative context.
  - Structured records must retain the primary entity ID and title as headers in every split chunk so that chunks returned during retrieval maintain semantic clarity and accurate citations.

---

## ADR 05: Defensive Guardrails and Exploit Refusal
- **Decision**: Enforce client-side and API-side safety checks that refuse offensive exploit generation, payload construction, and malware authoring.
- **Rationale**:
  - Ensures compliance with responsible AI principles.
  - Preserves CyberSense's core purpose as a defensive security decision-support tool.
  - Automatically redirects users toward remediation and detection best practices.

---

## ADR 06: Deterministic `FakeLLMClient` for Automated Testing and CI
- **Decision**: Implement a native `FakeLLMClient` that yields deterministic, cited responses for unit and integration testing.
- **Rationale**:
  - Enables full test suite and CI execution without requiring third-party API keys or internet access.
  - Fast test execution with zero flakiness from external rate limits.
