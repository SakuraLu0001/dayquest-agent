"""Claim-level provenance and conservative status semantics for DayQuest."""

from __future__ import annotations

from typing import Any


CLAIM_SCHEMA_VERSION = "dayquest.timeline_claim.v1"
CLAIM_CHECKER_VERSION = "dayquest.timeline_claim_checker.v1"
CLAIM_STATUSES = {"Supported", "Unknown", "Conflict"}


def _matches(record: dict[str, Any], requirement: dict[str, Any]) -> bool:
    return all(record.get(field) == value for field, value in requirement["match"].items())


def build_timeline_claim(
    contract: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build one focal claim without filling missing evidence."""

    pointers: list[dict[str, str]] = []
    missing: list[str] = []
    contradicted: list[str] = []
    for requirement in contract["required_evidence"]:
        matches = [record for record in events if _matches(record, requirement)]
        if not matches:
            missing.append(requirement["evidence_id"])
            continue
        record = matches[0]
        evidence_role = requirement.get("evidence_role", "supporting")
        pointers.append(
            {
                "source": record["source"],
                "safe_record_id": record["safe_event_id"],
                "identity_schema": record["safe_identity_schema"],
                "field": requirement["pointer_field"],
                "evidence_role": evidence_role,
                "evidence_id": requirement["evidence_id"],
            }
        )
        if evidence_role == "contradicting":
            contradicted.append(requirement["evidence_id"])

    supporting = [
        pointer for pointer in pointers if pointer["evidence_role"] == "supporting"
    ]
    if contradicted and supporting:
        status = "Conflict"
    elif missing:
        status = "Unknown"
    else:
        status = "Supported"
    claim = {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "run_id": contract["run_id"],
        "claim_id": contract["focal_claim"]["claim_id"],
        "statement": contract["focal_claim"]["statement"],
        "time_range": contract["focal_claim"]["time_range"],
        "status": status,
        "source_pointers": sorted(pointers, key=lambda item: item["evidence_id"]),
        "privacy_transforms": contract["focal_claim"]["privacy_transforms"],
        "required_evidence": [
            requirement["evidence_id"] for requirement in contract["required_evidence"]
        ],
        "missing_required_evidence": sorted(missing),
        "contradictions": sorted(contradicted),
        "decision_reason": (
            "supporting_and_contradicting_evidence_present"
            if status == "Conflict"
            else "required_evidence_missing"
            if missing
            else "all_required_evidence_present"
        ),
        "checker_version": CLAIM_CHECKER_VERSION,
    }
    if claim["status"] not in CLAIM_STATUSES:
        raise ValueError("invalid_claim_status")
    return claim
