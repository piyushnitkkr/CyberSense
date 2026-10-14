"""CISA Known Exploited Vulnerabilities (KEV) loader."""

from __future__ import annotations

import hashlib
import time
from typing import Iterator

import requests

from cybersense.ingestion.base import BaseLoader
from cybersense.logging import get_logger
from cybersense.models import DocType, Document

logger = get_logger(__name__)

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


class KEVLoader(BaseLoader):
    source_name = "kev"

    def __init__(self, request_delay: float = 0.6) -> None:
        self.request_delay = request_delay

    def load(self, **kwargs) -> Iterator[Document]:  # noqa: ARG002
        """Fetch the CISA KEV JSON feed and yield one Document per entry."""
        logger.info("Fetching CISA KEV feed", extra={"url": KEV_URL})
        try:
            resp = requests.get(KEV_URL, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Failed to fetch KEV feed", extra={"error": str(exc)})
            return

        data = resp.json()
        vulnerabilities = data.get("vulnerabilities", [])
        logger.info("KEV: fetched entries", extra={"count": len(vulnerabilities)})

        for entry in vulnerabilities:
            try:
                yield self._to_document(entry)
            except Exception as exc:
                logger.warning(
                    "KEV: skipping entry",
                    extra={"cve": entry.get("cveID"), "error": str(exc)},
                )

    def _to_document(self, entry: dict) -> Document:
        cve_id = entry.get("cveID", "UNKNOWN")
        title = f"{cve_id}: {entry.get('vulnerabilityName', '')}"
        text = (
            f"{title}\n"
            f"Vendor/Product: {entry.get('vendorProject', '')} / {entry.get('product', '')}\n"
            f"Description: {entry.get('shortDescription', '')}\n"
            f"Required Action: {entry.get('requiredAction', '')}\n"
            f"Due Date: {entry.get('dueDate', '')}\n"
            f"Date Added: {entry.get('dateAdded', '')}\n"
            f"Known Ransomware Campaign Use: {entry.get('knownRansomwareCampaignUse', '')}\n"
            f"Notes: {entry.get('notes', '')}"
        )
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        return Document(
            doc_id=f"kev:{cve_id}",
            source="kev",
            title=title,
            url=f"https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
            doc_type=DocType.kev,
            text=text,
            metadata={
                "cve_id": cve_id,
                "published_date": entry.get("dateAdded"),
                "due_date": entry.get("dueDate"),
                "vendor": entry.get("vendorProject"),
                "product": entry.get("product"),
                "ransomware_campaign": entry.get("knownRansomwareCampaignUse"),
            },
            content_hash=content_hash,
        )
