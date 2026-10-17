"""Unit tests for citation extraction, validation, and invalid reference stripping."""

from __future__ import annotations

from cybersense.generation.citations import build_citations, extract_citation_numbers
from cybersense.models import ChunkMetadata, RetrievedChunk


def _make_chunk(index: int, title: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"chk-{index}",
        text=f"Content for chunk number {index}.",
        score=0.9,
        metadata=ChunkMetadata(
            source="owasp",
            doc_id=f"doc-{index}",
            doc_type="prose",
            title=title,
            url=f"https://example.com/doc/{index}",
        ),
    )


def test_extract_citation_numbers():
    text = "Log4j [1] allows remote code execution [2] and bypasses controls [1]."
    nums = extract_citation_numbers(text)
    assert nums == [1, 2]


def test_build_citations_valid():
    chunks = [
        _make_chunk(1, "Log4j Advisory"),
        _make_chunk(2, "OWASP Injection Guide"),
    ]
    raw_answer = "This issue is described in [1] and remediated in [2]."
    cleaned, citations = build_citations(raw_answer, chunks)

    assert cleaned == raw_answer
    assert len(citations) == 2
    assert citations[0].n == 1
    assert citations[0].title == "Log4j Advisory"
    assert citations[1].n == 2
    assert citations[1].title == "OWASP Injection Guide"


def test_build_citations_strips_out_of_bounds_citations():
    # Only 2 chunks available, but answer mentions [1], [5], [99]
    chunks = [
        _make_chunk(1, "Doc 1"),
        _make_chunk(2, "Doc 2"),
    ]
    raw_answer = "Verified by [1], but also hallucinates [5] and [99]."
    cleaned, citations = build_citations(raw_answer, chunks)

    # [5] and [99] must be stripped
    assert "[5]" not in cleaned
    assert "[99]" not in cleaned
    assert "[1]" in cleaned
    assert len(citations) == 1
    assert citations[0].n == 1
