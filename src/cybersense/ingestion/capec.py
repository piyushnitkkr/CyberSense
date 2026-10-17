"""MITRE CAPEC loader — parses the XML from capec.mitre.org."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

from cybersense.ingestion.base import BaseLoader
from cybersense.logging import get_logger
from cybersense.models import DocType, Document

logger = get_logger(__name__)

_CAPEC_URL = "https://capec.mitre.org/data/xml/capec_latest.xml"
_NS = {"capec": "http://capec.mitre.org/capec-3"}


class CAPECLoader(BaseLoader):
    source_name = "capec"

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir

    def load(self, **kwargs) -> Iterator[Document]:
        xml_bytes = self._fetch_or_cache()
        root = ET.fromstring(xml_bytes)
        patterns = root.findall(".//capec:Attack_Pattern", _NS)
        logger.info("CAPEC: loaded patterns", extra={"count": len(patterns)})

        for p in patterns:
            try:
                yield self._to_document(p)
            except Exception as exc:
                logger.warning(
                    "CAPEC: skipping pattern",
                    extra={"id": p.get("ID"), "error": str(exc)},
                )

    def _fetch_or_cache(self) -> bytes:
        if self.cache_dir:
            cache_file = self.cache_dir / "capec_latest.xml"
            if cache_file.exists():
                return cache_file.read_bytes()

        logger.info("CAPEC: downloading XML", extra={"url": _CAPEC_URL})
        resp = requests.get(_CAPEC_URL, timeout=60)
        resp.raise_for_status()
        xml_bytes = resp.content

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            (self.cache_dir / "capec_latest.xml").write_bytes(xml_bytes)

        return xml_bytes

    def _get_text(self, elem: ET.Element, tag: str) -> str:
        child = elem.find(f"capec:{tag}", _NS)
        return "".join(child.itertext()).strip() if child is not None else ""

    def _to_document(self, p: ET.Element) -> Document:
        capec_id = f"CAPEC-{p.get('ID', '')}"
        name = p.get("Name", "")
        title = f"{capec_id}: {name}"
        description = self._get_text(p, "Description")
        likelihood = p.get("Likelihood_Of_Attack", "")
        severity = p.get("Typical_Severity", "")

        text = (
            f"{title}\n"
            f"Likelihood: {likelihood} | Severity: {severity}\n\n"
            f"Description:\n{description}"
        )
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        return Document(
            doc_id=f"capec:{capec_id}",
            source="capec",
            title=title,
            url=f"https://capec.mitre.org/data/definitions/{p.get('ID')}.html",
            doc_type=DocType.technique,
            text=text,
            metadata={
                "capec_id": capec_id,
                "likelihood": likelihood,
                "severity": severity,
            },
            content_hash=content_hash,
        )
