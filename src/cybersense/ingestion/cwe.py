"""MITRE CWE loader — parses the XML research view from cwe.mitre.org."""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from typing import Iterator
from xml.etree import ElementTree as ET

import requests

from cybersense.ingestion.base import BaseLoader
from cybersense.logging import get_logger
from cybersense.models import DocType, Document

logger = get_logger(__name__)

_CWE_URL = "https://cwe.mitre.org/data/xml/cwec_latest.xml.zip"
_NS = {"cwe": "http://cwe.mitre.org/cwe-7"}


class CWELoader(BaseLoader):
    source_name = "cwe"

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir

    def load(self, **kwargs) -> Iterator[Document]:
        xml_bytes = self._fetch_or_cache()
        root = ET.fromstring(xml_bytes)
        weaknesses = root.findall(".//cwe:Weakness", _NS)
        logger.info("CWE: loaded weaknesses", extra={"count": len(weaknesses)})

        for w in weaknesses:
            try:
                yield self._to_document(w)
            except Exception as exc:
                logger.warning(
                    "CWE: skipping weakness",
                    extra={"id": w.get("ID"), "error": str(exc)},
                )

    def _fetch_or_cache(self) -> bytes:
        if self.cache_dir:
            cache_file = self.cache_dir / "cwec_latest.xml"
            if cache_file.exists():
                logger.info("CWE: loading from cache", extra={"path": str(cache_file)})
                return cache_file.read_bytes()

        logger.info("CWE: downloading XML", extra={"url": _CWE_URL})
        resp = requests.get(_CWE_URL, timeout=60)
        resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            xml_name = next(n for n in zf.namelist() if n.endswith(".xml"))
            xml_bytes = zf.read(xml_name)

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / "cwec_latest.xml"
            cache_file.write_bytes(xml_bytes)

        return xml_bytes

    def _get_text(self, elem: ET.Element, tag: str) -> str:
        child = elem.find(f"cwe:{tag}", _NS)
        if child is None:
            return ""
        return "".join(child.itertext()).strip()

    def _to_document(self, w: ET.Element | dict) -> Document:
        if isinstance(w, dict):
            raw_id = str(w.get("@ID") or w.get("ID", ""))
            cwe_id = f"CWE-{raw_id}" if not raw_id.startswith("CWE-") else raw_id
            name = w.get("@Name") or w.get("Name", "")
            title = f"{cwe_id}: {name}" if name else cwe_id
            description = w.get("Description", "")
            likelihood = w.get("Likelihood_Of_Exploit", "")
            text = (
                f"{title}\n"
                f"Likelihood: {likelihood}\n\n"
                f"Description:\n{description}"
            )
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            return Document(
                doc_id=f"cwe:{cwe_id}",
                source="cwe",
                title=title,
                url=f"https://cwe.mitre.org/data/definitions/{raw_id}.html",
                doc_type=DocType.weakness,
                text=text,
                metadata={
                    "cwe_id": cwe_id,
                    "likelihood": likelihood,
                },
                content_hash=content_hash,
            )

        raw_id = w.get("ID", "")
        cwe_id = f"CWE-{raw_id}"
        name = w.get("Name", "")
        title = f"{cwe_id}: {name}"

        description = self._get_text(w, "Description")
        extended = self._get_text(w, "Extended_Description")
        likelihood = w.get("Likelihood_Of_Exploit", "")

        # Consequences
        consequences_el = w.find("cwe:Common_Consequences", _NS)
        consequences = ""
        if consequences_el is not None:
            parts = []
            for con in consequences_el.findall("cwe:Consequence", _NS):
                scope = self._get_text(con, "Scope")
                impact = self._get_text(con, "Impact")
                if scope or impact:
                    parts.append(f"Scope: {scope}; Impact: {impact}")
            consequences = "\n".join(parts)

        # Mitigations
        mitigations_el = w.find("cwe:Potential_Mitigations", _NS)
        mitigations = ""
        if mitigations_el is not None:
            parts = []
            for mit in mitigations_el.findall("cwe:Mitigation", _NS):
                desc = self._get_text(mit, "Description")
                if desc:
                    parts.append(desc)
            mitigations = "\n".join(parts)

        text = (
            f"{title}\n"
            f"Likelihood: {likelihood}\n\n"
            f"Description:\n{description}\n\n"
            f"{extended}\n\n"
            f"Consequences:\n{consequences}\n\n"
            f"Mitigations:\n{mitigations}"
        )
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        return Document(
            doc_id=f"cwe:{cwe_id}",
            source="cwe",
            title=title,
            url=f"https://cwe.mitre.org/data/definitions/{raw_id}.html",
            doc_type=DocType.weakness,
            text=text,
            metadata={
                "cwe_id": cwe_id,
                "likelihood": likelihood,
            },
            content_hash=content_hash,
        )
