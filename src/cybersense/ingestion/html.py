"""HTML loader using BeautifulSoup — for advisories and web pages."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from cybersense.ingestion.base import BaseLoader
from cybersense.logging import get_logger
from cybersense.models import DocType, Document

logger = get_logger(__name__)


class HTMLLoader(BaseLoader):
    source_name = "html"

    def __init__(
        self, source_label: str = "advisory", doc_type: DocType = DocType.advisory
    ) -> None:
        self.source_label = source_label
        self.doc_type = doc_type

    def load(
        self,
        urls: list[str] | None = None,
        paths: list[Path] | None = None,
        **kwargs,
    ) -> Iterator[Document]:
        for url in urls or []:
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                yield self._html_to_document(resp.text, url=url)
            except Exception as exc:
                logger.warning("HTML: skipping URL", extra={"url": url, "error": str(exc)})

        for path in paths or []:
            try:
                html = path.read_text(encoding="utf-8", errors="replace")
                yield self._html_to_document(html, path=path)
            except Exception as exc:
                logger.warning("HTML: skipping file", extra={"path": str(path), "error": str(exc)})

    def _html_to_document(self, html: str, url: str = "", path: Path | None = None) -> Document:
        soup = BeautifulSoup(html, "lxml")

        # Remove script/style noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title_el = soup.find("title")
        title = title_el.get_text(strip=True) if title_el else (path.stem if path else "Unknown")
        text = soup.get_text(separator="\n", strip=True)
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        doc_id = (
            f"{self.source_label}:{hashlib.sha256((url or str(path)).encode()).hexdigest()[:12]}"
        )

        return Document(
            doc_id=doc_id,
            source=self.source_label,
            title=title,
            url=url,
            doc_type=self.doc_type,
            text=text,
            metadata={"file_path": str(path) if path else ""},
            content_hash=content_hash,
        )
