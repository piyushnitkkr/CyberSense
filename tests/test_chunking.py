"""Unit tests for chunking strategies."""

from __future__ import annotations

from cybersense.ingestion.chunking import (
    ChunkingConfig,
    _approx_tokens,
    _split_by_headings,
    _split_by_tokens,
    chunk_prose_document,
    chunk_structured_record,
)
from cybersense.models import DocType, Document


def test_approx_tokens():
    assert _approx_tokens("abcd") == 1
    assert _approx_tokens("12345678") == 2
    assert _approx_tokens("") == 1


def test_split_by_tokens():
    text = "word " * 100
    chunks = _split_by_tokens(text, target=30, overlap=10)
    assert len(chunks) > 1
    # Check that overlap exists between consecutive chunks
    first_chunk_words = set(chunks[0].split())
    second_chunk_words = set(chunks[1].split())
    assert len(first_chunk_words & second_chunk_words) > 0


def test_split_by_headings():
    markdown = """# Introduction
This is the introductory section with some details.

## Technical Details
Here are the deep technical specifics and code blocks.

### Remediation
Apply patches and rotate credentials.
"""
    sections = _split_by_headings(markdown)
    assert len(sections) == 3
    assert sections[0][0] == "Introduction"
    assert sections[1][0] == "Technical Details"
    assert sections[2][0] == "Remediation"


def test_chunk_structured_record_short():
    doc = Document(
        doc_id="CVE-2023-1234",
        source="nvd",
        doc_type=DocType.cve,
        title="CVE-2023-1234 Short Record",
        text="A buffer overflow vulnerability exists in example service.",
        content_hash="hash123",
    )
    cfg = ChunkingConfig(max_tokens=800)
    chunks = chunk_structured_record(doc, cfg)
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "CVE-2023-1234:0"
    assert "CVE-2023-1234 Short Record" in chunks[0].text
    assert "CVE-2023-1234" in chunks[0].metadata.ids


def test_chunk_structured_record_long_repeats_header():
    body = "Very long vulnerability description with extensive details. " * 80
    doc = Document(
        doc_id="CWE-79",
        source="cwe",
        doc_type=DocType.weakness,
        title="CWE-79: Cross-site Scripting",
        text=body,
        content_hash="hash456",
    )
    cfg = ChunkingConfig(target_tokens=50, max_tokens=100, min_tokens=10, overlap_tokens=10)
    chunks = chunk_structured_record(doc, cfg)
    assert len(chunks) > 1
    # Every chunk must start with the title header for retrieval visibility
    for chunk in chunks:
        assert chunk.text.startswith("CWE-79: Cross-site Scripting")


def test_chunk_prose_document_headings():
    body = """# Policy
This security policy mandates multi-factor authentication across all external access points.

# Implementation
Administrators must configure SAML 2.0 or FIDO2 webauthn keys for all user sessions.
"""
    doc = Document(
        doc_id="doc-nist-sp800-63b",
        source="nist",
        doc_type=DocType.standard,
        title="NIST SP 800-63B Authentication",
        text=body,
        content_hash="hash789",
    )
    cfg = ChunkingConfig(min_tokens=5, max_tokens=200)
    chunks = chunk_prose_document(doc, cfg)
    assert len(chunks) == 2
    assert "Policy" in chunks[0].metadata.section_path
    assert "Implementation" in chunks[1].metadata.section_path
