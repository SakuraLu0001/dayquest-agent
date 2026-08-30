"""Two-case task evaluation for the first evidence-carrying timeline slice."""

from __future__ import annotations

import re
from typing import Any

from .evaluation import CANONICAL_JSON_HASH_BASIS, canonical_json, sha256_text
from .timeline_claims import build_timeline_claim


TASK_CASE_SCHEMA_VERSION = "dayquest.timeline_task_case.v1"
TASK_REPORT_SCHEMA_VERSION = "dayquest.timeline_task_report.v1"
TASK_AGGREGATE_SCHEMA_VERSION = "dayquest.timeline_task_aggregate.v1"
SLICE_ID = "DQ-TOP1-VS1-MCP-PROVENANCE-STATUS"
SLICE_BOUNDARY = (
    "Two-case synthetic-safe localhost MCP development slice; not production reliability, "
    "private-data applicability, or statistical generalization evidence."
)
_ABSOLUTE_WINDOWS_PATH = re.compile(r"\b[A-Za-z]:[\\/]")
_PRIVATE_TEXT = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?i)\b(?:bearer\s+|sk-)[A-Za-z0-9._-]{8,}"),
)


def execute_timeline_case(
    contract: dict[str, Any],
    transport_result: dict[str, Any],
) -> dict[str, Any]:
    if contract.get("schema_version") != TASK_CASE_SCHEMA_VERSION:
        raise ValueError("unsupported_timeline_case_schema")
    claim = build_timeline_claim(contract, transport_result["events"])
    expected_status = contract["expected_claim_status"]
    status_match = claim["status"] == expected_status
    required_ids = {
        requirement["evidence_id"] for requirement in contract["required_evidence"]
    }
    pointer_ids = {pointer["evidence_id"] for pointer in claim["source_pointers"]}
    missing_ids = set(claim["missing_required_evidence"])
    source_pointer_complete = (
        pointer_ids == required_ids if expected_status == "Supported" else None
    )
    missing_requirement_complete = (
        missing_ids == set(contract["expected_missing_evidence"])
        if expected_status == "Unknown"
        else None
    )
    false_supported = claim["status"] == "Supported" and expected_status != "Supported"
    task_verdict = "supported" if all(
        (
            status_match,
            transport_result["transport"]["real_transport"] is True,
            source_pointer_complete is not False,
            missing_requirement_complete is not False,
            not false_supported,
        )
    ) else "failed"
    return {
        "schema_version": TASK_REPORT_SCHEMA_VERSION,
        "slice_id": SLICE_ID,
        "case_id": contract["case_id"],
        "run_id": contract["run_id"],
        "case_contract_sha256": sha256_text(canonical_json(contract)),
        "case_contract_hash_basis": CANONICAL_JSON_HASH_BASIS,
        "fixture_id": contract["fixture_id"],
        "minimal_pair_delta": contract["minimal_pair_delta"],
        "transport": transport_result["transport"],
        "timeline": [claim],
        "evaluation": {
            "expected_claim_status": expected_status,
            "observed_claim_status": claim["status"],
            "status_exact_match": status_match,
            "source_pointer_complete": source_pointer_complete,
            "missing_requirement_complete": missing_requirement_complete,
            "false_supported": false_supported,
            "expected_task_verdict": contract["expected_task_verdict"],
            "observed_task_verdict": task_verdict,
            "task_verdict_match": task_verdict == contract["expected_task_verdict"],
        },
        "privacy": {
            "secret_required": False,
            "raw_private_material_stored": False,
            "absolute_path_stored": False,
        },
        "claim_boundary": SLICE_BOUNDARY,
    }


def build_timeline_aggregate(reports: list[dict[str, Any]]) -> dict[str, Any]:
    serialized = canonical_json(reports)
    privacy_leaks = int(
        bool(
            _ABSOLUTE_WINDOWS_PATH.search(serialized)
            or any(pattern.search(serialized) for pattern in _PRIVATE_TEXT)
        )
    )
    claims = [report["timeline"][0] for report in reports]
    return {
        "schema_version": TASK_AGGREGATE_SCHEMA_VERSION,
        "slice_id": SLICE_ID,
        "case_ids": [report["case_id"] for report in reports],
        "counts": {
            "total": len(reports),
            "real_mcp_transport": sum(
                report["transport"]["real_transport"] is True for report in reports
            ),
            "supported_claims": sum(claim["status"] == "Supported" for claim in claims),
            "unknown_claims": sum(claim["status"] == "Unknown" for claim in claims),
            "conflict_claims": sum(claim["status"] == "Conflict" for claim in claims),
            "status_exact_match": sum(
                report["evaluation"]["status_exact_match"] for report in reports
            ),
            "source_pointer_complete": sum(
                report["evaluation"]["source_pointer_complete"] is True
                for report in reports
            ),
            "missing_requirement_complete": sum(
                report["evaluation"]["missing_requirement_complete"] is True
                for report in reports
            ),
            "false_supported": sum(
                report["evaluation"]["false_supported"] for report in reports
            ),
            "task_verdict_match": sum(
                report["evaluation"]["task_verdict_match"] for report in reports
            ),
            "privacy_or_absolute_path_leaks": privacy_leaks,
        },
        "report_sha256": {
            report["case_id"]: sha256_text(canonical_json(report)) for report in reports
        },
        "report_hash_basis": CANONICAL_JSON_HASH_BASIS,
        "claim_boundary": SLICE_BOUNDARY,
    }
