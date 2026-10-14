"""Shared library used by both the ingest CLI script and the API route."""

from __future__ import annotations

from pathlib import Path

from cybersense.config import Settings
from cybersense.ingestion.base import BaseLoader

_RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

SOURCES = ["kev", "attack", "cwe", "capec", "nvd", "owasp", "nist"]


def get_loader_for_source(source: str, settings: Settings) -> BaseLoader:
    """Return the appropriate loader for *source*."""
    cache = _RAW_DIR / source
    cfg = settings.ingestion

    if source == "kev":
        from cybersense.ingestion.kev import KEVLoader
        return KEVLoader(request_delay=cfg.request_delay_seconds)

    if source == "attack":
        from cybersense.ingestion.attack import ATTACKLoader
        return ATTACKLoader(cache_dir=cache)

    if source == "cwe":
        from cybersense.ingestion.cwe import CWELoader
        return CWELoader(cache_dir=cache)

    if source == "capec":
        from cybersense.ingestion.capec import CAPECLoader
        return CAPECLoader(cache_dir=cache)

    if source == "nvd":
        from cybersense.ingestion.nvd import NVDLoader
        return NVDLoader(
            api_key=settings.nvd_api_key,
            lookback_days=cfg.nvd_lookback_days,
            request_delay=cfg.request_delay_seconds,
        )

    if source == "owasp":
        from cybersense.ingestion.markdown import MarkdownLoader
        from cybersense.models import DocType
        return MarkdownLoader(source_label="owasp", doc_type=DocType.guide)

    if source == "nist":
        from cybersense.ingestion.pdf import PDFLoader
        from cybersense.models import DocType
        return PDFLoader(source_label="nist", doc_type=DocType.standard)

    raise ValueError(f"Unknown source: {source!r}. Valid: {SOURCES}")
