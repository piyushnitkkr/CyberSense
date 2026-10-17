"""NVD CVE loader — uses the NVD REST API 2.0."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Iterator
from datetime import datetime, timedelta

import requests

from cybersense.ingestion.base import BaseLoader
from cybersense.logging import get_logger
from cybersense.models import DocType, Document

logger = get_logger(__name__)

_NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_PAGE_SIZE = 2000


class NVDLoader(BaseLoader):
    source_name = "nvd"

    def __init__(
        self,
        api_key: str = "",
        lookback_days: int = 730,
        request_delay: float = 0.6,
        kev_cve_ids: list[str] | None = None,
    ) -> None:
        self.api_key = api_key
        self.lookback_days = lookback_days
        self.request_delay = request_delay
        self.kev_cve_ids = kev_cve_ids or []

    def load(
        self, since: str | None = None, limit: int | None = None, **kwargs
    ) -> Iterator[Document]:
        headers = {"apiKey": self.api_key} if self.api_key else {}
        start_date = (
            datetime.fromisoformat(since)
            if since
            else datetime.utcnow() - timedelta(days=self.lookback_days)
        )
        pub_start = start_date.strftime("%Y-%m-%dT00:00:00.000")
        pub_end = datetime.utcnow().strftime("%Y-%m-%dT23:59:59.999")

        start_index = 0
        total_yielded = 0

        while True:
            if limit and total_yielded >= limit:
                break

            params: dict = {
                "pubStartDate": pub_start,
                "pubEndDate": pub_end,
                "startIndex": start_index,
                "resultsPerPage": min(_PAGE_SIZE, (limit - total_yielded) if limit else _PAGE_SIZE),
            }

            try:
                resp = requests.get(_NVD_API, params=params, headers=headers, timeout=60)
                resp.raise_for_status()
            except requests.RequestException as exc:
                logger.error("NVD: request failed", extra={"error": str(exc)})
                break

            data = resp.json()
            vulns = data.get("vulnerabilities", [])
            if not vulns:
                break

            for item in vulns:
                try:
                    doc = self._to_document(item["cve"])
                    yield doc
                    total_yielded += 1
                    if limit and total_yielded >= limit:
                        return
                except Exception as exc:
                    logger.warning(
                        "NVD: skipping CVE",
                        extra={"id": item.get("cve", {}).get("id"), "error": str(exc)},
                    )

            start_index += len(vulns)
            total_results = data.get("totalResults", 0)
            logger.info(
                "NVD: paged",
                extra={"start": start_index, "total": total_results, "yielded": total_yielded},
            )

            if start_index >= total_results:
                break

            time.sleep(self.request_delay)

    def _to_document(self, cve: dict) -> Document:
        cve_id = cve.get("id", "")
        descriptions = cve.get("descriptions", [])
        en_desc = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")

        # CVSS score
        metrics = cve.get("metrics", {})
        cvss_score = None
        severity = None
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if key in metrics and metrics[key]:
                cvss_data = metrics[key][0].get("cvssData", {})
                cvss_score = cvss_data.get("baseScore")
                severity = cvss_data.get("baseSeverity") or metrics[key][0].get("baseSeverity")
                break

        refs = cve.get("references", [])
        ref_urls = [r.get("url", "") for r in refs[:5]]

        title = f"{cve_id}: {en_desc[:80]}..." if len(en_desc) > 80 else f"{cve_id}: {en_desc}"
        text = (
            f"{cve_id}\n"
            f"Severity: {severity or 'N/A'} | CVSS: {cvss_score or 'N/A'}\n\n"
            f"Description:\n{en_desc}\n\n"
            f"References:\n" + "\n".join(ref_urls)
        )
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        pub_date = cve.get("published", "")

        return Document(
            doc_id=f"nvd:{cve_id}",
            source="nvd",
            title=title,
            url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            doc_type=DocType.cve,
            text=text,
            metadata={
                "cve_id": cve_id,
                "cvss": cvss_score,
                "severity": severity,
                "published_date": pub_date,
                "modified_date": cve.get("lastModified"),
            },
            content_hash=content_hash,
        )
