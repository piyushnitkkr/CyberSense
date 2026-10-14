"""Citation extraction and validation from generated answers."""

from __future__ import annotations

import re

from cybersense.models import Citation, RetrievedChunk

_CITATION_RE = re.compile(r"\[(\d+)\]")


def extract_citation_numbers(text: str) -> list[int]:
    """Return sorted list of unique citation numbers found in *text*."""
    nums = [int(m) for m in _CITATION_RE.findall(text)]
    return sorted(set(nums))


def build_citations(
    answer: str,
    chunks: list[RetrievedChunk],
) -> tuple[str, list[Citation]]:
    """Validate and build structured Citation objects.

    - Strip any [n] references to chunks that don't exist.
    - Return (cleaned_answer, citations).
    """
    used_nums = extract_citation_numbers(answer)
    valid_nums = {n for n in used_nums if 1 <= n <= len(chunks)}

    # Strip invalid references from the answer
    def _replace(m: re.Match) -> str:
        n = int(m.group(1))
        return m.group(0) if n in valid_nums else ""

    cleaned = _CITATION_RE.sub(_replace, answer).strip()

    citations: list[Citation] = []
    for n in sorted(valid_nums):
        chunk = chunks[n - 1]
        meta = chunk.metadata
        citations.append(
            Citation(
                n=n,
                title=meta.title,
                source=meta.source,
                section_path=meta.section_path,
                url=meta.url,
                page=meta.page,
                snippet=chunk.text[:300].strip(),
            )
        )

    return cleaned, citations
