"""Deterministic privacy detection and redaction."""

from __future__ import annotations

import json
import re
from dataclasses import replace

from .models import Event


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\w)")
AMOUNT_RE = re.compile(r"\$\s?\d+(?:\.\d{2})?")
ORDER_RE = re.compile(r"(?i)\b(?:order\s*)?(?:DQ-)?\d{4,}\b")
ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+(?:[A-Z][\w'-]*\s+){0,3}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b",
    re.IGNORECASE,
)

GENERALIZATIONS = {
    "Northbridge Language Center": "a certification hall",
    "Arcadia Innovation Hall": "the event venue",
    "Juniper Cup": "a local café",
    "MetroLink": "local transit",
}


def detect_private_data(text: str) -> list[tuple[str, str, str]]:
    """Return (category, matched value, treatment) tuples."""
    findings: list[tuple[str, str, str]] = []
    for category, pattern, treatment in (
        ("email address", EMAIL_RE, "removed"),
        ("phone number", PHONE_RE, "removed"),
        ("exact amount", AMOUNT_RE, "generalized"),
        ("order number", ORDER_RE, "removed"),
        ("specific street address", ADDRESS_RE, "generalized"),
    ):
        findings.extend((category, match.group(0), treatment) for match in pattern.finditer(text))
    lowered = text.lower()
    for original in GENERALIZATIONS:
        if original.lower() in lowered:
            findings.append(("institution or merchant name", original, "generalized"))
    return findings


def redact_text(text: str) -> str:
    safe = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    safe = PHONE_RE.sub("[REDACTED_PHONE]", safe)
    safe = AMOUNT_RE.sub("a small purchase", safe)
    safe = ORDER_RE.sub("[REDACTED_ORDER]", safe)
    safe = ADDRESS_RE.sub("near the venue", safe)
    for original, replacement in GENERALIZATIONS.items():
        safe = re.sub(re.escape(original), replacement, safe, flags=re.IGNORECASE)
    return safe


def redact_events(events: list[Event]) -> tuple[list[Event], dict[str, list[str]]]:
    report: dict[str, list[str]] = {"Detected": [], "Removed": [], "Generalized": []}
    safe_events: list[Event] = []
    for event in events:
        searchable = f"{event.summary} {json.dumps(event.evidence, ensure_ascii=False)}"
        findings = detect_private_data(searchable)
        for category, _value, treatment in findings:
            label = f"{event.event_id}: {category}"
            if label not in report["Detected"]:
                report["Detected"].append(label)
            bucket = "Removed" if treatment == "removed" else "Generalized"
            if label not in report[bucket]:
                report[bucket].append(label)
        safe_events.append(
            replace(
                event,
                summary=redact_text(event.summary),
                sensitivity="redacted" if findings else "low",
                evidence={"status": "source evidence withheld after privacy processing"},
                redacted=bool(findings),
            )
        )
    return safe_events, report


def contains_forbidden_data(text: str) -> bool:
    return bool(detect_private_data(text))

