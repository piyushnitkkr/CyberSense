"""Unit tests for source loaders and data normalization."""

from __future__ import annotations

from cybersense.ingestion.attack import ATTACKLoader
from cybersense.ingestion.cwe import CWELoader
from cybersense.ingestion.kev import KEVLoader
from cybersense.models import DocType


def test_kev_loader_to_document():
    loader = KEVLoader()
    raw_entry = {
        "cveID": "CVE-2023-34362",
        "vendorProject": "Progress",
        "product": "MOVEit Transfer",
        "vulnerabilityName": "Progress MOVEit Transfer SQL Injection",
        "dateAdded": "2023-06-02",
        "shortDescription": "Progress MOVEit Transfer contains a SQL injection vulnerability.",
        "requiredAction": "Apply mitigations per vendor instructions.",
        "dueDate": "2023-06-23",
        "knownRansomwareCampaignUse": "Known",
        "notes": "Exploited by CL0P ransomware group.",
    }
    doc = loader._to_document(raw_entry)

    assert doc.doc_id == "kev:CVE-2023-34362"
    assert doc.source == "kev"
    assert doc.doc_type == DocType.kev
    assert "CVE-2023-34362" in doc.title
    assert "CL0P ransomware" in doc.text
    assert doc.metadata["ransomware_campaign"] == "Known"
    assert doc.metadata["cve_id"] == "CVE-2023-34362"


def test_attack_loader_to_document():
    loader = ATTACKLoader()
    raw_obj = {
        "id": "attack-pattern--12345",
        "type": "attack-pattern",
        "name": "PowerShell",
        "description": "Adversaries may use PowerShell commands and scripts.",
        "external_references": [
            {
                "source_name": "mitre-attack",
                "external_id": "T1059.001",
                "url": "https://attack.mitre.org/techniques/T1059/001",
            }
        ],
        "kill_chain_phases": [{"kill_chain_name": "mitre-attack", "phase_name": "execution"}],
        "x_mitre_platforms": ["Windows"],
        "x_mitre_detection": "Monitor PowerShell script block logging (Event ID 4104).",
        "x_mitre_is_subtechnique": True,
        "modified": "2023-04-15T00:00:00.000Z",
    }
    doc = loader._to_document(raw_obj, [raw_obj])

    assert doc.doc_id == "attack:T1059.001"
    assert doc.source == "attack"
    assert doc.doc_type == DocType.technique
    assert "T1059.001 PowerShell" in doc.title
    assert "Event ID 4104" in doc.text
    assert doc.metadata["attack_id"] == "T1059.001"
    assert "execution" in doc.metadata["tactics"]
    assert doc.metadata["is_subtechnique"] is True


def test_cwe_loader_to_document():
    loader = CWELoader()
    raw_weakness = {
        "@ID": "89",
        "@Name": "Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')",
        "Description": "The product constructs all or part of an SQL command using untrusted input.",
        "Likelihood_Of_Exploit": "High",
    }
    doc = loader._to_document(raw_weakness)

    assert doc.doc_id == "cwe:CWE-89"
    assert doc.source == "cwe"
    assert doc.doc_type == DocType.weakness
    assert "CWE-89" in doc.title
    assert "SQL Command" in doc.text
    assert doc.metadata["cwe_id"] == "CWE-89"
    assert doc.metadata["likelihood"] == "High"
