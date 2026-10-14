"""MITRE ATT&CK loader — reads the STIX 2.1 JSON bundle from GitHub."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterator

import requests

from cybersense.ingestion.base import BaseLoader
from cybersense.logging import get_logger
from cybersense.models import DocType, Document

logger = get_logger(__name__)

_ATTACK_URL = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/"
    "master/enterprise-attack/enterprise-attack.json"
)


class ATTACKLoader(BaseLoader):
    source_name = "attack"

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir

    def load(self, **kwargs) -> Iterator[Document]:
        """Load ATT&CK Enterprise techniques from STIX JSON."""
        stix = self._fetch_or_cache()
        objects = stix.get("objects", [])
        techniques = [o for o in objects if o.get("type") == "attack-pattern"]
        logger.info("ATT&CK: loaded techniques", extra={"count": len(techniques)})

        # Build lookup for kill-chain phase names
        for obj in techniques:
            try:
                yield self._to_document(obj, objects)
            except Exception as exc:
                logger.warning(
                    "ATT&CK: skipping object",
                    extra={"id": obj.get("id"), "error": str(exc)},
                )

    def _fetch_or_cache(self) -> dict:
        if self.cache_dir:
            cache_file = self.cache_dir / "enterprise-attack.json"
            if cache_file.exists():
                logger.info("ATT&CK: loading from cache", extra={"path": str(cache_file)})
                return json.loads(cache_file.read_text(encoding="utf-8"))

        logger.info("ATT&CK: downloading STIX bundle", extra={"url": _ATTACK_URL})
        resp = requests.get(_ATTACK_URL, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / "enterprise-attack.json"
            cache_file.write_text(json.dumps(data), encoding="utf-8")
            logger.info("ATT&CK: cached", extra={"path": str(cache_file)})

        return data

    def _to_document(self, obj: dict, all_objects: list[dict]) -> Document:
        ext_ref = obj.get("external_references", [])
        attack_id = next(
            (r.get("external_id", "") for r in ext_ref if r.get("source_name") == "mitre-attack"),
            "",
        )
        url = next(
            (r.get("url", "") for r in ext_ref if r.get("source_name") == "mitre-attack"),
            "",
        )
        name = obj.get("name", "")
        description = obj.get("description", "")
        phases = [p.get("phase_name", "") for p in obj.get("kill_chain_phases", [])]
        platforms = obj.get("x_mitre_platforms", [])
        detection = obj.get("x_mitre_detection", "")
        is_subtechnique = obj.get("x_mitre_is_subtechnique", False)

        title = f"{attack_id} {name}" if attack_id else name
        text = (
            f"{title}\n"
            f"Tactic: {', '.join(phases)}\n"
            f"Platforms: {', '.join(platforms)}\n\n"
            f"Description:\n{description}\n\n"
            f"Detection:\n{detection}"
        )
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        return Document(
            doc_id=f"attack:{attack_id or obj['id']}",
            source="attack",
            title=title,
            url=url,
            doc_type=DocType.technique,
            text=text,
            metadata={
                "attack_id": attack_id,
                "tactics": phases,
                "platforms": platforms,
                "is_subtechnique": is_subtechnique,
                "modified_date": obj.get("modified"),
            },
            content_hash=content_hash,
        )
