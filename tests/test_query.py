"""Unit tests for query ID extraction and Reciprocal Rank Fusion (RRF)."""

from __future__ import annotations

from cybersense.ingestion.enrich import extract_ids
from cybersense.models import ChunkMetadata, RetrievedChunk
from cybersense.retrieval.hybrid import reciprocal_rank_fusion


def test_extract_cve_ids():
    text = "Investigating CVE-2021-44228 and CVE-2023-34362 in log systems."
    ids = extract_ids(text)
    assert "CVE-2021-44228" in ids
    assert "CVE-2023-34362" in ids


def test_extract_cwe_ids():
    text = "The application suffers from CWE-79 and CWE-89 injection."
    ids = extract_ids(text)
    assert "CWE-79" in ids
    assert "CWE-89" in ids


def test_extract_attack_technique_ids():
    text = "Adversaries execute code via T1059.001 and dump credentials using T1003.001."
    ids = extract_ids(text)
    assert "T1059.001" in ids
    assert "T1003.001" in ids


def test_extract_nist_controls():
    text = "Implementation of AC-2 and IA-2 controls is mandatory for federal systems."
    ids = extract_ids(text)
    assert "AC-2" in ids
    assert "IA-2" in ids


def _make_dummy_chunk(chunk_id: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=f"Text for {chunk_id}",
        score=score,
        metadata=ChunkMetadata(
            source="test",
            doc_id=chunk_id.split(":")[0],
            doc_type="structured",
            title=f"Doc {chunk_id}",
        ),
    )


def test_reciprocal_rank_fusion():
    dense_list = [
        _make_dummy_chunk("doc-A:0", 0.9),
        _make_dummy_chunk("doc-B:0", 0.8),
        _make_dummy_chunk("doc-C:0", 0.7),
    ]
    sparse_list = [
        _make_dummy_chunk("doc-B:0", 15.0),
        _make_dummy_chunk("doc-D:0", 12.0),
        _make_dummy_chunk("doc-A:0", 10.0),
    ]

    # doc-B is rank 2 in dense and rank 1 in sparse -> should get highest reciprocal rank
    fused = reciprocal_rank_fusion(dense_list, sparse_list, k=60, top_n=4)
    assert len(fused) == 4
    # doc-B should be top since it's rank 1 and 2
    assert fused[0].chunk_id == "doc-B:0"
    assert fused[1].chunk_id == "doc-A:0"
    assert fused[0].score > fused[1].score


def test_reciprocal_rank_fusion_empty():
    fused = reciprocal_rank_fusion([], [])
    assert fused == []
