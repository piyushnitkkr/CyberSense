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
                yield self._pdf_to_document_stream(filepath, fitz)
            except Exception as exc:
                logger.warning(
                    "PDF: skipping file",
                    extra={"path": str(filepath), "error": str(exc)},
                )

    def _pdf_to_document_stream(self, path: Path, fitz) -> Document:
        """Stream PDF processing to minimize memory usage - process one page at a time."""
        doc = fitz.open(str(path))

        # Memory-conscious limits for Render's 512MB free tier
        max_pages = 15  # Further reduced for safety
        max_chars_per_page = 3000  # ~750 tokens per page max
        max_total_chars = 25000  # ~6250 tokens total (~25 chunks of 250 chars)

        processed_chars = 0
        processed_pages = 0
        all_text_parts = []  # Will hold limited text chunks

        try:
            for page_num in range(min(len(doc), max_pages)):
                page = doc[page_num]
                text = page.get_text("text") or ""

                if not text.strip():
                    continue

                # Limit text per page to prevent memory spikes
                if len(text) > max_chars_per_page:
                    text = text[:max_chars_per_page] + "... [truncated]"
                    logger.info(f"PDF: page {page_num} text truncated to {max_chars_per_page} chars")

                # Check if adding this page would exceed total limit
                if processed_chars + len(text) > max_total_chars:
                    logger.info(f"PDF: reached total char limit at page {page_num}")
                    break

                all_text_parts.append(text)
                processed_chars += len(text)
                processed_pages += 1

        finally:
            doc.close()
            # Explicit cleanup
            del doc
            import gc
            gc.collect()

        # Join text with minimal overhead
        full_text = "\n\n".join(all_text_parts)
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
                "page_count": processed_pages,
            },
            content_hash=content_hash,
        )
