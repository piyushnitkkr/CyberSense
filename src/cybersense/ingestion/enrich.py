"""Metadata enrichment: extract cybersecurity IDs from text."""

from __future__ import annotations

import re

# ── ID regexes ────────────────────────────────────────────────────────────────
_CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE)
_CWE_RE = re.compile(r"\bCWE-\d+\b", re.IGNORECASE)
_CAPEC_RE = re.compile(r"\bCAPEC-\d+\b", re.IGNORECASE)
_ATTACK_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")
_NIST_CTRL_RE = re.compile(r"\b[A-Z]{2}-\d+(?:\(\d+\))?\b")  # e.g. AC-2, AU-12(1)


def extract_ids(text: str) -> list[str]:
    """Return a deduplicated list of all cybersecurity IDs found in *text*."""
    found: list[str] = []
    for pattern in (_CVE_RE, _CWE_RE, _CAPEC_RE, _ATTACK_RE, _NIST_CTRL_RE):
        found.extend(m.upper() for m in pattern.findall(text))
    return list(dict.fromkeys(found))  # preserve order, deduplicate
