"""Markdown loader — OWASP Top 10, Cheat Sheets, and other Markdown sources."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path

from cybersense.ingestion.base import BaseLoader
from cybersense.logging import get_logger
from cybersense.models import DocType, Document

logger = get_logger(__name__)


class MarkdownLoader(BaseLoader):
    """Load one or many Markdown files from a directory or list of paths."""

    source_name = "markdown"

    def __init__(self, source_label: str = "owasp", doc_type: DocType = DocType.guide) -> None:
        self.source_label = source_label
        self.doc_type = doc_type

    def load(
        self, paths: list[Path] | None = None, directory: Path | None = None, **kwargs
    ) -> Iterator[Document]:
        files: list[Path] = list(paths or [])
        if directory and directory.is_dir():
            files.extend(sorted(directory.rglob("*.md")))
            files.extend(sorted(directory.rglob("*.markdown")))

        logger.info(
            "Markdown: loading files", extra={"source": self.source_label, "count": len(files)}
        )

        for filepath in files:
            try:
                yield self._file_to_document(filepath)
            except Exception as exc:
                logger.warning(
                    "Markdown: skipping file",
                    extra={"path": str(filepath), "error": str(exc)},
                )

    def _file_to_document(self, path: Path) -> Document:
        text = path.read_text(encoding="utf-8", errors="replace")
        title = path.stem.replace("-", " ").replace("_", " ").title()
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        doc_id = f"{self.source_label}:{path.stem}"

        return Document(
            doc_id=doc_id,
            source=self.source_label,
            title=title,
            url="",
            doc_type=self.doc_type,
            text=text,
            metadata={"file_path": str(path)},
            content_hash=content_hash,
        )
