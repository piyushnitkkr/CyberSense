"""PDF loader using PyMuPDF — for NIST publications and user uploads."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterator

from cybersense.ingestion.base import BaseLoader
from cybersense.logging import get_logger
from cybersense.models import DocType, Document

logger = get_logger(__name__)


class PDFLoader(BaseLoader):
    source_name = "pdf"

    def __init__(self, source_label: str = "nist", doc_type: DocType = DocType.standard) -> None:
        self.source_label = source_label
        self.doc_type = doc_type

    def load(self, paths: list[Path] | None = None, directory: Path | None = None, **kwargs) -> Iterator[Document]:
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("PyMuPDF not installed — cannot load PDFs")
            return

        files: list[Path] = list(paths or [])
        if directory and directory.is_dir():
            files.extend(sorted(directory.rglob("*.pdf")))

        logger.info("PDF: loading files", extra={"source": self.source_label, "count": len(files)})

        for filepath in files:
            try:
                yield self._pdf_to_document(filepath, fitz)
            except Exception as exc:
                logger.warning(
                    "PDF: skipping file",
                    extra={"path": str(filepath), "error": str(exc)},
                )

    def _pdf_to_document(self, path: Path, fitz) -> Document:
        doc = fitz.open(str(path))
        pages_text: list[str] = []
        # Cap to first 50 pages to prevent memory exhaustion on free tier
        max_pages = 50
        # Also cap total text length to prevent chunking OOM (approx 500KB of text)
        max_text_length = 500_000
        total_text_length = 0

        for i, page in enumerate(doc):
            if i >= max_pages:
                logger.info("PDF: reached max_pages limit", extra={"max_pages": max_pages, "total_pages": len(doc)})
                break
            text = page.get_text("text") or ""
            if text.strip():
                # Check if adding this page would exceed the text limit
                if total_text_length + len(text) > max_text_length:
                    logger.info("PDF: reached max_text_length limit", extra={"max_text_length": max_text_length, "total_pages_processed": i})
                    break
                pages_text.append(text)
                total_text_length += len(text)
        doc.close()
        del doc
        import gc
        gc.collect()

        full_text = "\n\n".join(pages_text)
        title = path.stem.replace("-", " ").replace("_", " ").title()
        content_hash = hashlib.sha256(full_text.encode()).hexdigest()
        doc_id = f"{self.source_label}:{path.stem}"

        return Document(
            doc_id=doc_id,
            source=self.source_label,
            title=title,
            url="",
            doc_type=self.doc_type,
            text=full_text,
            metadata={
                "file_path": str(path),
                "page_count": len(pages_text),
            },
            content_hash=content_hash,
        )
