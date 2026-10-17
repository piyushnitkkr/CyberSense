"""MITRE ATT&CK loader — Enterprise + ICS + Mobile STIX 2.1 bundles."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

import requests

from cybersense.ingestion.base import BaseLoader
from cybersense.logging import get_logger
from cybersense.models import DocType, Document

logger = get_logger(__name__)

_BUNDLES = {
    "enterprise": (
        "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/"
        "master/enterprise-attack/enterprise-attack.json"
    ),
    "ics": (
        "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/"
        "master/ics-attack/ics-attack.json"
    ),
    "mobile": (
        "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/"
        "master/mobile-attack/mobile-attack.json"
    ),
}


class ATTACKLoader(BaseLoader):
    source_name = "attack"

    def __init__(self, cache_dir: Path | None = None, bundles: list[str] | None = None) -> None:
        self.cache_dir = cache_dir
        # Default: load all three bundles for maximum coverage
        self.bundles = bundles or list(_BUNDLES.keys())

    def load(self, **kwargs) -> Iterator[Document]:
        """Load ATT&CK techniques from Enterprise + ICS + Mobile STIX bundles."""
        seen_ids: set[str] = set()  # deduplicate across bundles

        for bundle_name in self.bundles:
            url = _BUNDLES.get(bundle_name)
            if not url:
                logger.warning("ATT&CK: unknown bundle", extra={"bundle": bundle_name})
                continue
            try:
                stix = self._fetch_or_cache(bundle_name, url)
            except Exception as exc:
                logger.warning(
                    "ATT&CK: failed to load bundle",
                    extra={"bundle": bundle_name, "error": str(exc)},
                )
                continue

            objects = stix.get("objects", [])
            techniques = [
                o for o in objects if o.get("type") == "attack-pattern" and not o.get("revoked")
            ]
            # Build lookup maps from this bundle
            mitigation_map = _build_mitigation_map(objects)
            data_source_map = _build_data_source_map(objects)

            logger.info(
                "ATT&CK: loaded techniques",
                extra={"bundle": bundle_name, "count": len(techniques)},
            )

            for obj in techniques:
                attack_id = _get_attack_id(obj)
                if attack_id in seen_ids:
                    continue
                seen_ids.add(attack_id)
                try:
                    yield self._to_document(
                        obj, attack_id, bundle_name, mitigation_map, data_source_map
                    )
                except Exception as exc:
                    logger.warning(
                        "ATT&CK: skipping object",
                        extra={"id": obj.get("id"), "error": str(exc)},
                    )

    def _fetch_or_cache(self, bundle_name: str, url: str) -> dict:
        if self.cache_dir:
            cache_file = self.cache_dir / f"{bundle_name}-attack.json"
            if cache_file.exists():
                logger.info("ATT&CK: loading from cache", extra={"path": str(cache_file)})
                return json.loads(cache_file.read_text(encoding="utf-8"))

        logger.info("ATT&CK: downloading STIX bundle", extra={"url": url})
        resp = requests.get(url, timeout=180)
        resp.raise_for_status()
        data = resp.json()

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / f"{bundle_name}-attack.json"
            cache_file.write_text(json.dumps(data), encoding="utf-8")
            logger.info("ATT&CK: cached", extra={"path": str(cache_file)})

        return data

    def _to_document(
        self,
        obj: dict,
        attack_id_or_objects: str | list[dict] | None = None,
        bundle_name: str = "enterprise",
        mitigation_map: dict[str, list[str]] | None = None,
        data_source_map: dict[str, list[str]] | None = None,
    ) -> Document:
        if isinstance(attack_id_or_objects, list):
            attack_id = _get_attack_id(obj)
            mitigation_map = _build_mitigation_map(attack_id_or_objects)
            data_source_map = _build_data_source_map(attack_id_or_objects)
        elif isinstance(attack_id_or_objects, str):
            attack_id = attack_id_or_objects
        else:
            attack_id = _get_attack_id(obj)

        if mitigation_map is None:
            mitigation_map = {}
        if data_source_map is None:
            data_source_map = {}

        ext_ref = obj.get("external_references", [])
        url = next(
            (r.get("url", "") for r in ext_ref if r.get("source_name") == "mitre-attack"),
            "",
        )
        name = obj.get("name", "")
        description = obj.get("description", "")
        phases = [
            p.get("phase_name", "").replace("-", " ") for p in obj.get("kill_chain_phases", [])
        ]
        platforms = obj.get("x_mitre_platforms", [])
        detection = obj.get("x_mitre_detection", "")
        is_subtechnique = obj.get("x_mitre_is_subtechnique", False)
        permissions = obj.get("x_mitre_permissions_required", [])
        defenses_bypassed = obj.get("x_mitre_defense_bypassed", [])
        data_sources = obj.get("x_mitre_data_sources", [])

        # Look up mitigations and enriched data sources from relationship map
        mitigations = mitigation_map.get(obj.get("id", ""), [])
        enriched_sources = data_source_map.get(obj.get("id", ""), [])
        all_data_sources = list(dict.fromkeys(data_sources + enriched_sources))  # deduplicate

        title = f"{attack_id} {name}" if attack_id else name

        # Build a rich, structured text body
        sections = [
            f"{title}",
            f"Domain: {bundle_name.replace('_', ' ').title()} ATT&CK",
            f"Tactic(s): {', '.join(phases) if phases else 'N/A'}",
            f"Platforms: {', '.join(platforms) if platforms else 'N/A'}",
            f"Sub-technique: {'Yes' if is_subtechnique else 'No'}",
        ]
        if permissions:
            sections.append(f"Permissions Required: {', '.join(permissions)}")
        if defenses_bypassed:
            sections.append(f"Defenses Bypassed: {', '.join(defenses_bypassed)}")

        sections.append(f"\nDescription:\n{description}")

        if detection:
            sections.append(f"\nDetection:\n{detection}")

        if all_data_sources:
            sections.append(f"\nData Sources: {', '.join(all_data_sources)}")

        if mitigations:
            sections.append("\nMitigations:\n" + "\n".join(f"- {m}" for m in mitigations))

        text = "\n".join(sections)
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
                "bundle": bundle_name,
                "modified_date": obj.get("modified"),
            },
            content_hash=content_hash,
        )


# ── STIX helper functions ─────────────────────────────────────────────────────


def _get_attack_id(obj: dict) -> str:
    """Extract the ATT&CK ID (e.g. T1059) from external references."""
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return ref.get("external_id", "")
    return ""


def _build_mitigation_map(objects: list[dict]) -> dict[str, list[str]]:
    """Return {technique_stix_id: [mitigation_name, ...]} from STIX relationships."""
    # Index course-of-action objects by id
    mitigations: dict[str, str] = {
        o["id"]: o.get("name", "") for o in objects if o.get("type") == "course-of-action"
    }
    result: dict[str, list[str]] = {}
    for rel in objects:
        if (
            rel.get("type") == "relationship"
            and rel.get("relationship_type") == "mitigates"
            and rel.get("source_ref", "") in mitigations
        ):
            target = rel["target_ref"]
            name = mitigations[rel["source_ref"]]
            result.setdefault(target, []).append(name)
    return result


def _build_data_source_map(objects: list[dict]) -> dict[str, list[str]]:
    """Return {technique_stix_id: [data_source_name, ...]} from STIX x-mitre-data-source objects."""
    ds_names: dict[str, str] = {
        o["id"]: o.get("name", "") for o in objects if o.get("type") == "x-mitre-data-source"
    }
    result: dict[str, list[str]] = {}
    for rel in objects:
        if (
            rel.get("type") == "relationship"
            and rel.get("relationship_type") == "detects"
            and rel.get("source_ref", "") in ds_names
        ):
            target = rel["target_ref"]
            name = ds_names[rel["source_ref"]]
            result.setdefault(target, []).append(name)
    return result
