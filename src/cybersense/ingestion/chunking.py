"""Text chunking strategies for structured records and prose documents."""

from __future__ import annotations

import re
from dataclasses import dataclass

from cybersense.models import Chunk, ChunkMetadata, Document


@dataclass
class ChunkingConfig:
    target_tokens: int = 512
    max_tokens: int = 800
    min_tokens: int = 50
    overlap_tokens: int = 64


def _approx_tokens(text: str) -> int:
    """Rough token count: ~4 chars per token for English."""
    return max(1, len(text) // 4)


def _split_by_tokens(
    text: str,
    target: int,
    overlap: int,
) -> list[str]:
    """Split text into overlapping windows based on approximate token count."""
    words = text.split()
    if not words:
        return []

    # Convert token counts to word counts (tokens ≈ 1.3 words on average)
    target_words = max(1, int(target * 1.3))
    overlap_words = max(0, int(overlap * 1.3))

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + target_words, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap_words
    return chunks


# Heading patterns for heading-aware splitting
_HEADING_RE = re.compile(r"^(#{1,6}\s+.+|[^\n]+\n[=\-]{3,})", re.MULTILINE)


def _split_by_headings(text: str) -> list[tuple[str, str]]:
    """Return list of (section_path, section_text) tuples split at Markdown headings."""
    sections: list[tuple[str, str]] = []
    positions = [(m.start(), m.group()) for m in _HEADING_RE.finditer(text)]

    if not positions:
        return [("", text)]

    for i, (pos, heading) in enumerate(positions):
        start = pos
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        section_text = text[start:end].strip()
        heading_text = heading.lstrip("#").strip().split("\n")[0]
        sections.append((heading_text, section_text))

    # Text before first heading
    preamble = text[: positions[0][0]].strip()
    if preamble:
        sections.insert(0, ("", preamble))

    return sections


def chunk_structured_record(
    doc: Document,
    cfg: ChunkingConfig,
) -> list[Chunk]:
    """One logical record → one or a few chunks (ATT&CK, CWE, CVE, KEV, CAPEC).

    ID and name are prepended to every chunk so they are always retrievable.
    """
    header = f"{doc.title}\n"
    body = doc.text
    full = header + body

    if _approx_tokens(full) <= cfg.max_tokens:
        return [_make_chunk(doc, 0, full, cfg)]

    # Split long records into field-group chunks, each starting with the header
    field_groups = _split_by_tokens(body, cfg.target_tokens, cfg.overlap_tokens)
    return [
        _make_chunk(doc, i, header + fg, cfg)
        for i, fg in enumerate(field_groups)
        if _approx_tokens(fg) >= cfg.min_tokens
    ]


def chunk_prose_document(
    doc: Document,
    cfg: ChunkingConfig,
    section_path_prefix: str = "",
) -> list[Chunk]:
    """Heading-aware recursive splitting for prose (NIST, OWASP, advisories)."""
    sections = _split_by_headings(doc.text)
    chunks: list[Chunk] = []
    idx = 0
    for heading, section_text in sections:
        path = f"{section_path_prefix} > {heading}".strip(" >") if heading else section_path_prefix

        if _approx_tokens(section_text) <= cfg.max_tokens:
            if _approx_tokens(section_text) >= cfg.min_tokens:
                chunks.append(_make_chunk(doc, idx, section_text, cfg, section_path=path))
                idx += 1
        else:
            for sub_text in _split_by_tokens(section_text, cfg.target_tokens, cfg.overlap_tokens):
                if _approx_tokens(sub_text) >= cfg.min_tokens:
                    chunks.append(_make_chunk(doc, idx, sub_text, cfg, section_path=path))
                    idx += 1

    # Fallback: if document has non-empty text but sections were shorter than min_tokens, preserve the text
    if not chunks and doc.text.strip():
        chunks.append(_make_chunk(doc, 0, doc.text.strip(), cfg, section_path=section_path_prefix))

    return chunks


def _make_chunk(
    doc: Document,
    index: int,
    text: str,
    cfg: ChunkingConfig,
    section_path: str = "",
) -> Chunk:
    from cybersense.ingestion.enrich import extract_ids

    meta = ChunkMetadata(
        source=doc.source,
        doc_id=doc.doc_id,
        doc_type=doc.doc_type.value,
        title=doc.title,
        section_path=section_path or doc.metadata.get("section_path", ""),
        url=doc.url,
        page=doc.metadata.get("page"),
        published_date=doc.metadata.get("published_date"),
        modified_date=doc.metadata.get("modified_date"),
        ids=extract_ids(text),
        severity=doc.metadata.get("severity"),
        cvss=doc.metadata.get("cvss"),
        content_hash=doc.content_hash,
    )
    return Chunk(
        chunk_id=f"{doc.doc_id}:{index}",
        doc_id=doc.doc_id,
        text=text,
        index=index,
        metadata=meta,
    )
