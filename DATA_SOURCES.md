# CyberSense RAG System - Data Sources Documentation

**Project**: CyberSense Cybersecurity RAG Chatbot  
**Purpose**: College Project - Retrieval Augmented Generation for Cybersecurity Knowledge  
**Date**: October 2026  
**Status**: Active Development

---

## Executive Summary

CyberSense integrates multiple authoritative cybersecurity data sources to provide comprehensive, accurate answers to security professionals. The system uses vector embeddings and hybrid retrieval (dense + sparse search) to return contextually relevant information with proper citations.

---

## Data Sources Integrated

### 1. **MITRE ATT&CK Enterprise (v9.0+)**
- **Source**: https://github.com/mitre-attack/attack-stix-data
- **Format**: STIX 2.1 JSON Collection
- **Size**: 52.7 MB
- **Content**: 
  - 867 Attack Techniques
  - Tactics and Kill Chain Phases
  - Detection Methods
  - Mitigation Strategies
  - Platform-specific Attack Patterns
- **License**: Creative Commons Attribution 4.0
- **URL**: https://owasp.org/www-project-top-ten/
- **Ingestion Script**: `scripts/ingest_attack.py`
- **Status**: ✅ Integrated (867 techniques indexed)

### 2. **MITRE CWE (Common Weakness Enumeration)**
- **Source**: https://cwe.mitre.org/
- **Format**: XML/JSON
- **Content**:
  - Common Software Weaknesses
  - Vulnerability Patterns
  - Weakness Relationships
  - Attack/Defense Insights
- **License**: Community Resource
- **Ingestion Script**: `scripts/ingest_cwe.py`
- **Status**: ✅ Integrated

### 3. **OWASP Top 10 (2025)**
- **Source**: https://github.com/OWASP/Top10
- **Format**: Markdown + JSON
- **Versions Available**: 
  - 2025 (Latest)
  - 2021
  - 2017
  - 2013
  - 2010
  - 2007
  - 2004
  - 2003
- **Content**:
  - A1: Broken Access Control
  - A2: Cryptographic Failures
  - A3: Injection
  - A4: Insecure Design
  - A5: Security Misconfiguration
  - A6: Vulnerable and Outdated Components
  - A7: Identification and Authentication Failures
  - A8: Software and Data Integrity Failures
  - A9: Logging and Monitoring Failures
  - A10: Security Logging and Monitoring Failures
- **License**: Creative Commons Attribution-ShareAlike 4.0
- **Ingestion Script**: `scripts/ingest_owasp.py`
- **Status**: ✅ Integrated (10 items)

### 4. **NVD (National Vulnerability Database)**
- **Source**: https://nvd.nist.gov/
- **Format**: JSON Feed
- **Content**:
  - CVE (Common Vulnerabilities and Exposures)
  - CVSS Scores
  - CWE References
  - Severity Ratings
  - Affected Products
- **License**: Public Domain (U.S. Government)
- **Ingestion Script**: Built-in NVD loader (optional ingestion)
- **Status**: ⚙️ Available for ingestion

### 5. **NIST Cybersecurity Framework (CSF)**
- **Source**: https://nvlpubs.nist.gov/nist-pubs/
- **Format**: PDF + Documentation
- **Content**:
  - Core Functions (Identify, Protect, Detect, Respond, Recover)
  - Categories and Subcategories
  - Implementation Guidance
  - Outcomes
- **License**: Public Domain (NIST Publication)
- **Status**: 📋 Recommended for ingestion

### 6. **NIST SP 800-53 (Security Controls)**
- **Source**: https://nvlpubs.nist.gov/nist-pubs/800-53r5/
- **Format**: PDF
- **Content**:
  - 400+ Security Controls
  - AC (Access Control)
  - AU (Audit and Accountability)
  - AT (Awareness and Training)
  - SC (System and Communications Protection)
  - IA (Identification and Authentication)
  - And 14+ other families
- **License**: Public Domain
- **Status**: 📋 Recommended for ingestion

### 7. **CIS Critical Security Controls (v8)**
- **Source**: https://www.cisecurity.org/
- **Format**: Documentation
- **Content**:
  - 18 Critical Controls
  - Implementation Groups (IG1, IG2, IG3)
  - Sub-controls with guidance
  - Metrics and KPIs
- **License**: Community Edition (Free)
- **Status**: 📋 Recommended for ingestion

### 8. **ISO 27001/27002 Security Controls**
- **Source**: ISO/IEC Standards
- **Format**: XML/Documentation
- **Content**:
  - 93 Security Controls
  - Information Security Policies
  - Asset Management
  - Cryptography
  - Physical and Environmental Security
  - Operations Security
  - Communications Security
  - System Acquisition and Maintenance
  - Supplier Relationships
  - Information Security Incident Management
  - Business Continuity Management
  - Compliance
- **License**: ISO Standard (Paid)
- **Status**: 📋 Can integrate open-source summaries

### 9. **User-Uploaded Documents**
- **Source**: Streamlit Sidebar Upload
- **Format**: PDF, DOCX, MD, TXT, HTML
- **Content**:
  - Custom Security Policies
  - Organization-Specific Guidelines
  - Internal Procedures
  - Risk Assessments
  - Compliance Documentation
- **Max Size**: 25 MB per file
- **Status**: ✅ Active (temporary storage during session)

### 10. **Test Cybersecurity Policy (Sample)**
- **Source**: `data/test_cybersecurity_policy.md`
- **Format**: Markdown
- **Content**:
  - Sample organizational policy
  - Access Control (AC) controls
  - Audit & Accountability (AU) controls
  - System Protection (SC) controls
  - Incident Response (IR) controls
  - Risk Assessment (RA) controls
  - And 5+ more families
- **Status**: ✅ Available for testing

---

## Data Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Data Sources                         │
├─────────────────────────────────────────────────────────────────┤
│  • MITRE ATT&CK      • OWASP Top 10      • NVD              │
│  • MITRE CWE         • NIST CSF          • User Uploads      │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Ingestion Pipeline │
        │  (PDFLoader,       │
        │   ATTACKLoader,    │
        │   CWELoader)       │
        └────────┬───────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Chunking Engine    │
        │ (Text → Chunks)    │
        └────────┬───────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Embedding Model    │
        │ (BAAI/bge-small)   │
        │ 384-dim vectors    │
        └────────┬───────────┘
                 │
        ┌────────▼───────────┐
        │  Qdrant Vector DB  │
        │  3,610+ chunks     │
        │  (Persistent)      │
        └────────┬───────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ BM25 Sparse Index  │
        │ (In-memory)        │
        └────────────────────┘
```

---

## Retrieval Pipeline

When a user asks a question:

1. **Query Rewriting**: Preserve cybersecurity terminology
2. **Entity Extraction**: Extract CVE-XXXX, CWE-XXX, T#### IDs
3. **Dense Search**: Vector similarity in Qdrant (3,610 chunks)
4. **Sparse Search**: BM25 keyword matching
5. **Fusion**: Reciprocal Rank Fusion (RRF)
6. **Reranking**: Optional semantic reranking
7. **Relevance Check**: Removed aggressive threshold
8. **LLM Generation**: Answer with citations

---

## Statistics

| Metric | Value |
|--------|-------|
| **Total Chunks Indexed** | 3,610+ |
| **MITRE ATT&CK Techniques** | 867 |
| **Vector Dimension** | 384 |
| **Embedding Model** | BAAI/bge-small-en-v1.5 |
| **Vector DB** | Qdrant (Cloud) |
| **Sparse Index** | BM25 (In-memory) |
| **Max File Upload** | 25 MB |
| **Supported Formats** | PDF, DOCX, MD, TXT, HTML |
| **Chunk Size** | 512-800 tokens (target 512) |
| **Max Chunks/Doc** | 3 (per document) |

---

## Deployment

**Production**: Render (Free tier 512MB)
- **Backend API**: https://cybersense-api-vorj.onrender.com
- **Vector DB**: Qdrant Cloud (Managed)
- **Database**: SQLite (aiosqlite)
- **LLM Provider**: Groq API (Llama 3.1 8B)

---

## Future Data Sources (Roadmap)

- [ ] **CAPEC** (Common Attack Pattern Enumeration)
- [ ] **CVRF** (Common Vulnerability Reporting Framework)
- [ ] **STIX** (Structured Threat Information Expression)
- [ ] **TAXII** (Trusted Automated eXchange of Indicator Information)
- [ ] **OSCAL** (Open Security Controls Assessment Language)
- [ ] **Shodan/CVE Data** (Real-time vulnerability feeds)
- [ ] **GitHub Security Advisories**
- [ ] **CISA KEV (Known Exploited Vulnerabilities)**

---

## Data Quality & Maintenance

- **Update Frequency**: Weekly (ATT&CK, CWE, NVD)
- **Validation**: Ingestion pipeline checks for duplicates
- **Caching**: 24-hour in-memory cache for downloaded datasets
- **Versioning**: Track ingestion run history in DB
- **Deduplication**: 200-char signature-based near-duplicate removal
- **Per-Document Cap**: Max 3 chunks returned per source

---

## Compliance & Licensing

| Source | License | Commercial Use | Attribution |
|--------|---------|-----------------|--------------|
| MITRE ATT&CK | CC-BY 4.0 | ✅ Yes | Required |
| MITRE CWE | Community | ✅ Yes | Recommended |
| OWASP Top 10 | CC-BY-SA 4.0 | ✅ Yes | Required |
| NVD/NIST | Public Domain | ✅ Yes | No |
| CIS Controls | Community Edition | ✅ Yes (Limited) | Required |
| ISO 27001 | Proprietary | ❌ No (Paid) | Summaries only |

---

## Performance Metrics

- **Dense Search Latency**: ~3.7 sec (Qdrant Cloud)
- **Sparse Search Latency**: ~0.1 ms (Local BM25)
- **Fusion & Reranking**: ~0.1 ms
- **LLM Generation**: ~2-5 sec (Groq API)
- **Total Query Time**: ~6-9 seconds

---

## Example Queries & Expected Sources

| Query | Expected Sources |
|-------|------------------|
| "T1059 command injection" | MITRE ATT&CK, CWE |
| "access control policy" | NIST SP 800-53, OWASP |
| "SQL injection detection" | OWASP Top 10, CWE, NVD |
| "zero-trust architecture" | NIST CSF, Custom Policies |
| "incident response procedures" | NIST SP 800-61, Custom |

---

## Ingestion Scripts

Located in `scripts/`:

- `ingest_attack.py` - MITRE ATT&CK (867 techniques)
- `ingest_cwe.py` - MITRE CWE
- `ingest_owasp.py` - OWASP Top 10
- (Others in pipeline)

**Usage**:
```bash
.venv/Scripts/python scripts/ingest_attack.py
.venv/Scripts/python scripts/ingest_cwe.py
.venv/Scripts/python scripts/ingest_owasp.py
```

---

## References

- [MITRE ATT&CK](https://attack.mitre.org/)
- [MITRE CWE](https://cwe.mitre.org/)
- [OWASP](https://owasp.org/)
- [NIST Cybersecurity](https://www.nist.gov/cyberframework/)
- [Qdrant Vector Database](https://qdrant.tech/)
- [BAAI Embeddings](https://huggingface.co/BAAI/bge-small-en-v1.5)

---

**Document Version**: 1.0  
**Last Updated**: October 17, 2026  
**Author**: CyberSense Development Team  
**Status**: Active