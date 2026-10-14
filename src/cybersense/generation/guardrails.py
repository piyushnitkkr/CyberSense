"""Safety guardrails for input validation and output screening."""

from __future__ import annotations

import re

# ── Refusal patterns ──────────────────────────────────────────────────────────
_EXPLOIT_PATTERNS = [
    re.compile(r"\b(write|create|generate|give me|provide)\b.{0,40}\b(exploit|shellcode|payload|malware|ransomware|trojan|backdoor|rootkit|keylogger)\b", re.IGNORECASE),
    re.compile(r"\b(step.by.step|how to|instructions? for).{0,40}\b(hack|attack|break into|compromise|breach|pwn)\b.{0,40}\b(server|system|network|machine|host)\b", re.IGNORECASE),
    re.compile(r"\b(metasploit|msfvenom|cobalt strike).{0,30}(module|payload|script|generate)\b", re.IGNORECASE),
]

_REFUSAL_MESSAGE = (
    "I'm not able to help with that. CyberSense is designed for defensive security — "
    "understanding threats, detecting attacks, and improving security posture. "
    "For the defensive perspective on this topic, try asking: "
    "\"How is this technique detected?\" or \"What mitigations protect against this?\""
)

# ── Prompt injection patterns ─────────────────────────────────────────────────
_INJECTION_PATTERNS = [
    re.compile(r"ignore (previous|above|prior|all) instructions?", re.IGNORECASE),
    re.compile(r"disregard (?:(?:your|the)\s+)?(?:system|previous) (?:prompt|instructions?)", re.IGNORECASE),
    re.compile(r"you are now\b.{0,40}\bassistant", re.IGNORECASE),
    re.compile(r"<\|?(system|user|assistant)\|?>", re.IGNORECASE),
]


def check_input(user_message: str) -> str | None:
    """Return a refusal string if the message is disallowed, else None."""
    for pattern in _EXPLOIT_PATTERNS:
        if pattern.search(user_message):
            return _REFUSAL_MESSAGE
    return None


def sanitize_chunk_text(text: str) -> str:
    """Strip prompt-injection-like patterns from retrieved chunk text."""
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def validate_upload_filename(filename: str, allowed_extensions: list[str]) -> bool:
    """Return True if the filename has an allowed extension (case-insensitive)."""
    import pathlib
    ext = pathlib.Path(filename).suffix.lower()
    return ext in [e.lower() for e in allowed_extensions]
