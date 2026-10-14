"""Reciprocal Rank Fusion (RRF) hybrid retrieval fusion."""

from __future__ import annotations

from cybersense.models import RetrievedChunk

_RRF_K = 60  # standard constant


def reciprocal_rank_fusion(
    *ranked_lists: list[RetrievedChunk],
    k: int = _RRF_K,
    top_n: int = 30,
) -> list[RetrievedChunk]:
    """Fuse multiple ranked result lists with RRF.

    Args:
        *ranked_lists: Any number of ranked RetrievedChunk lists.
        k: RRF smoothing constant (default 60).
        top_n: Number of results to return.

    Returns:
        Merged and re-ranked list of RetrievedChunk.
    """
    scores: dict[str, float] = {}
    best_chunk: dict[str, RetrievedChunk] = {}

    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked, start=1):
            cid = chunk.chunk_id
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            # Keep the version with the highest original score as representative
            if cid not in best_chunk or chunk.score > best_chunk[cid].score:
                best_chunk[cid] = chunk

    sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:top_n]

    return [
        RetrievedChunk(
            chunk_id=cid,
            text=best_chunk[cid].text,
            score=scores[cid],
            metadata=best_chunk[cid].metadata,
        )
        for cid in sorted_ids
    ]
