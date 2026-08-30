"""Deterministic 12-case product workflow for the evidence-carrying timeline MVP."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .evaluation import CANONICAL_JSON_HASH_BASIS, canonical_json, sha256_text
from .mcp_timeline_client import fetch_timeline_inputs, running_local_mcp_server
from .pomerium_mcp_server import (
    SAFE_EVENT_FIELDS,
    SAFE_EVENT_ID_HASH_BASIS,
    SAFE_EVENT_ID_SCHEMA,
    stable_safe_event_id,
)
from .timeline_claims import build_timeline_claim


MVP_CASE_SCHEMA_VERSION = "dayquest.timeline_task_case.v2"
MVP_REPORT_SCHEMA_VERSION = "dayquest.timeline_mvp_report.v1"
MVP_AGGREGATE_SCHEMA_VERSION = "dayquest.timeline_mvp_aggregate.v1"
MVP_ID = "DQ-TOP1-MVP-TIMELINE-REVIEW-AND-12CASE-EVIDENCE01"
MVP_BOUNDARY = (
    "Twelve-case synthetic-safe local product acceptance matrix; not production "
    "reliability, private-data applicability, statistical generalization, or safety certification."
)

EXPECTED_CASE_IDS = [
    "DQ-TOP1-POSITIVE-001",
    "DQ-TOP1-POSITIVE-002",
    "DQ-TOP1-MISSING-001",
    "DQ-TOP1-MISSING-002",
    "DQ-TOP1-CONFLICT-001",
    "DQ-TOP1-CONFLICT-002",
    "DQ-TOP1-POLICY-001",
    "DQ-TOP1-POLICY-002",
    "DQ-TOP1-TOOL-FAILURE-001",
    "DQ-TOP1-TOOL-FAILURE-002",
    "DQ-TOP1-TOOL-FAILURE-003",
    "DQ-TOP1-TOOL-FAILURE-004",
]

REAL_MCP_CASE_IDS = set(EXPECTED_CASE_IDS[:8])
TOOL_FAILURE_CASE_IDS = set(EXPECTED_CASE_IDS[8:])

D3_REGRESSION_IDENTITIES = {
    "DQ-EVAL-BASELINE-001": (
        "artifacts/evaluation/day2/reports/DQ-EVAL-BASELINE-001.json",
        "881655C9D85CC8552414E490E377EA75E42270F48645D8C4014B700333C73824",
    ),
    "DQ-EVAL-LOCAL-ERROR-001": (
        "artifacts/evaluation/day2/reports/DQ-EVAL-LOCAL-ERROR-001.json",
        "0EB9A0824A8BBCD0FEB1D12BD775E0C62BF2FA841BD46857D2D896AAA75C8C16",
    ),
    "DQ-EVAL-MAX-ITERATION-001": (
        "artifacts/evaluation/day3/reports/DQ-EVAL-MAX-ITERATION-001.json",
        "E357EF6D54BA83CFBB80A43F2CC4DBC2795197475EDAE7B78049A1A8A6D22CA1",
    ),
    "DQ-EVAL-NEXLA-RECOVERY-001": (
        "artifacts/evaluation/day3/reports/DQ-EVAL-NEXLA-RECOVERY-001.json",
        "25A4C7F39396235B42E43AFDA27F73282124614E99E3EB31249B7102CFCC8E5D",
    ),
    "DQ-EVAL-POLICY-COUNTEREXAMPLE-001": (
        "artifacts/evaluation/day3/reports/DQ-EVAL-POLICY-COUNTEREXAMPLE-001.json",
        "17438FD2AC9568ED42629AE889AF6CB863FEE25F5857114D072C0CD3F254C673",
    ),
}

VS1_REGRESSION_IDENTITIES = {
    "aggregate": (
        "artifacts/evaluation/top1/vs1/aggregate.json",
        "5FEB610614070502AE9437049838CEDC74F96A13EFBA73923567217F9FD31499",
    ),
    "missing_report": (
        "artifacts/evaluation/top1/vs1/reports/DQ-TOP1-MISSING-001.json",
        "720E8B9CA9D1B57E74BDE0C49BE0F79DA6C188D50C56D01C669BD9CD558F5514",
    ),
    "positive_report": (
        "artifacts/evaluation/top1/vs1/reports/DQ-TOP1-POSITIVE-001.json",
        "46A2AFC92625DE6B2C97C3E682879B09887527117BA25269A2B21E7CB151D198",
    ),
}

_ABSOLUTE_WINDOWS_PATH = re.compile(r"\b[A-Za-z]:[\\/]")
_PRIVATE_TEXT = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?i)\b(?:bearer\s+|sk-)[A-Za-z0-9._-]{8,}"),
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _contains_private_material(value: Any) -> bool:
    serialized = canonical_json(value)
    return bool(
        _ABSOLUTE_WINDOWS_PATH.search(serialized)
        or any(pattern.search(serialized) for pattern in _PRIVATE_TEXT)
    )


def make_synthetic_safe_record(
    *,
    source: str,
    event_type: str,
    approximate_time: str,
    safe_summary: str,
) -> dict[str, Any]:
    """Build a fixture record through the same stable, privacy-safe identity basis."""

    identity_material = {
        "safe_identity_schema": SAFE_EVENT_ID_SCHEMA,
        "source": source,
        "event_type": event_type,
        "approximate_time": approximate_time,
        "safe_summary": safe_summary,
    }
    record = {
        "safe_event_id": stable_safe_event_id(identity_material),
        **identity_material,
        "sensitivity": "low",
        "redacted": True,
    }
    if set(record) != SAFE_EVENT_FIELDS:
        raise ValueError("synthetic_safe_record_schema_invalid")
    return record


def load_mvp_contracts(project_root: Path) -> list[dict[str, Any]]:
    contract_paths = [
        project_root
        / "artifacts"
        / "evaluation"
        / "top1"
        / "vs1"
        / "contracts"
        / "DQ-TOP1-POSITIVE-001.json",
        project_root
        / "artifacts"
        / "evaluation"
        / "top1"
        / "vs1"
        / "contracts"
        / "DQ-TOP1-MISSING-001.json",
    ]
    contract_paths.extend(
        sorted(
            (
                project_root
                / "artifacts"
                / "evaluation"
                / "top1"
                / "mvp"
                / "contracts"
            ).glob("*.json")
        )
    )
    contracts_by_id = {
        contract["case_id"]: contract
        for contract in (
            json.loads(path.read_text(encoding="utf-8")) for path in contract_paths
        )
    }
    if set(contracts_by_id) != set(EXPECTED_CASE_IDS):
        raise ValueError("unexpected_mvp_case_set")
    return [contracts_by_id[case_id] for case_id in EXPECTED_CASE_IDS]


def _scenario(contract: dict[str, Any]) -> dict[str, Any]:
    if "scenario" in contract:
        return contract["scenario"]
    return {
        "kind": "real_mcp",
        "tool_limit": contract["tool_limit"],
        "transform": "none",
        "terminal": "completed",
    }


def _family(case_id: str) -> str:
    if "POSITIVE" in case_id:
        return "positive"
    if "MISSING" in case_id:
        return "missing_evidence"
    if "CONFLICT" in case_id:
        return "conflict"
    if "POLICY" in case_id:
        return "policy_privacy"
    return "tool_failure"


def _base_contract_value(contract: dict[str, Any], key: str, default: Any) -> Any:
    return contract[key] if key in contract else default


def _transform_real_events(
    case_id: str,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if case_id in {
        "DQ-TOP1-POSITIVE-001",
        "DQ-TOP1-POSITIVE-002",
        "DQ-TOP1-MISSING-001",
        "DQ-TOP1-POLICY-001",
        "DQ-TOP1-POLICY-002",
    }:
        return copy.deepcopy(events)
    if case_id == "DQ-TOP1-MISSING-002":
        return [
            copy.deepcopy(record)
            for record in events
            if not (
                record["source"] == "calendar" and record["event_type"] == "hackathon"
            )
        ]
    if case_id == "DQ-TOP1-CONFLICT-001":
        supporting = next(
            record
            for record in events
            if record["source"] == "emails"
            and record["event_type"] == "exam_confirmation"
        )
        contradicting = make_synthetic_safe_record(
            source="calendar",
            event_type="language_exam",
            approximate_time="afternoon",
            safe_summary="Language certification exam scheduled for the afternoon.",
        )
        return [copy.deepcopy(supporting), contradicting]
    if case_id == "DQ-TOP1-CONFLICT-002":
        return [
            make_synthetic_safe_record(
                source="calendar",
                event_type="hackathon_location_guildhall",
                approximate_time="evening",
                safe_summary="Hackathon scheduled at Guild Hall.",
            ),
            make_synthetic_safe_record(
                source="transactions",
                event_type="hackathon_location_riverside",
                approximate_time="evening",
                safe_summary="Travel evidence points to Riverside Lab for the hackathon.",
            ),
        ]
    raise ValueError(f"unsupported_real_case:{case_id}")


def _fault_events(case_id: str) -> list[dict[str, Any]]:
    if case_id in {
        "DQ-TOP1-TOOL-FAILURE-002",
        "DQ-TOP1-TOOL-FAILURE-004",
    }:
        return [
            make_synthetic_safe_record(
                source="emails",
                event_type="exam_confirmation",
                approximate_time="morning",
                safe_summary="A safe certification exam reminder was observed.",
            )
        ]
    return []


def _policy_violations(contract: dict[str, Any], claim: dict[str, Any]) -> list[str]:
    policy_fault = _scenario(contract).get("policy_fault")
    violations: list[str] = []
    if policy_fault == "synthetic_privacy_sentinel":
        private_fixture = "Synthetic marker private.fixture@example.invalid"
        if any(pattern.search(private_fixture) for pattern in _PRIVATE_TEXT):
            violations.append("synthetic_privacy_sentinel_detected")
    if policy_fault == "story_consumes_non_supported" and claim["status"] != "Supported":
        violations.append("story_consumed_non_supported_claim")
    return violations


def _fault_transport(contract: dict[str, Any], event_count: int) -> dict[str, Any]:
    scenario = _scenario(contract)
    return {
        "endpoint": "localhost-mcp-fault-fixture",
        "transport": "controlled-fault-fixture",
        "real_transport": False,
        "fault_fixture": True,
        "local_only": True,
        "network_scope": "loopback_only",
        "secret_required": False,
        "event_count": event_count,
        "error_type": scenario["tool_fault"],
        "retry_attempts": 0,
        "safe_identity_schema": SAFE_EVENT_ID_SCHEMA,
        "safe_identity_hash_basis": SAFE_EVENT_ID_HASH_BASIS,
        "safe_identity_is_confidentiality_primitive": False,
    }


def evaluate_mvp_case(
    contract: dict[str, Any],
    events: list[dict[str, Any]],
    transport: dict[str, Any],
) -> dict[str, Any]:
    claim = build_timeline_claim(contract, events)
    scenario = _scenario(contract)
    expected_status = contract["expected_claim_status"]
    expected_task = contract["expected_task_verdict"]
    expected_policy = _base_contract_value(contract, "expected_policy_status", "compliant")
    policy_violations = _policy_violations(contract, claim)
    observed_policy = "violation" if policy_violations else "compliant"
    observed_task = (
        "failed"
        if observed_policy == "violation" or claim["status"] != expected_status
        else "supported"
    )

    supporting = [
        pointer
        for pointer in claim["source_pointers"]
        if pointer["evidence_role"] == "supporting"
    ]
    contradicting = [
        pointer
        for pointer in claim["source_pointers"]
        if pointer["evidence_role"] == "contradicting"
    ]
    expected_missing = sorted(contract.get("expected_missing_evidence", []))
    expected_contradictions = sorted(contract.get("expected_contradictions", []))
    missing_match = sorted(claim["missing_required_evidence"]) == expected_missing
    contradiction_match = sorted(claim["contradictions"]) == expected_contradictions
    is_tool_failure = contract["case_id"] in TOOL_FAILURE_CASE_IDS
    correct_tool_safe_behavior = (
        claim["status"] == "Unknown"
        and transport.get("retry_attempts", 0) == 0
        and scenario.get("terminal", "").startswith("safe_")
        if is_tool_failure
        else None
    )

    story_eligible = claim["status"] == "Supported" and observed_policy == "compliant"
    story_attempted = bool(scenario.get("story_attempt", False))
    story_facts = [claim["statement"]] if story_eligible else []
    false_supported = claim["status"] == "Supported" and expected_status != "Supported"
    false_failed = observed_task == "failed" and expected_task == "supported"

    report = {
        "schema_version": MVP_REPORT_SCHEMA_VERSION,
        "mvp_id": MVP_ID,
        "case_id": contract["case_id"],
        "family": _family(contract["case_id"]),
        "run_id": contract["run_id"],
        "case_contract_schema_version": contract["schema_version"],
        "case_contract_sha256": sha256_text(canonical_json(contract)),
        "case_contract_hash_basis": CANONICAL_JSON_HASH_BASIS,
        "user_goal": _base_contract_value(
            contract, "user_goal", "Build one conservative synthetic-safe timeline claim."
        ),
        "transport": transport,
        "timeline": [claim],
        "evidence_review": {
            "supporting_pointers": supporting,
            "contradicting_pointers": contradicting,
            "missing_requirements": claim["missing_required_evidence"],
        },
        "policy": {
            "expected": expected_policy,
            "observed": observed_policy,
            "violations": policy_violations,
            "separate_from_claim_status": True,
        },
        "tool_behavior": {
            "fault": scenario.get("tool_fault"),
            "terminal": scenario.get("terminal", "completed"),
            "retry_attempts": transport.get("retry_attempts", 0),
            "continued_allowed_sources": bool(
                scenario.get("continued_allowed_sources", False)
            ),
            "correct_safe_behavior": correct_tool_safe_behavior,
        },
        "story": {
            "eligible": story_eligible,
            "attempted": story_attempted,
            "factual_inputs": story_facts,
            "non_supported_fact_emitted": bool(
                story_facts and claim["status"] != "Supported"
            ),
        },
        "evaluation": {
            "expected_claim_status": expected_status,
            "observed_claim_status": claim["status"],
            "status_exact_match": claim["status"] == expected_status,
            "missing_requirements_match": missing_match,
            "contradictions_match": contradiction_match,
            "expected_task_verdict": expected_task,
            "observed_task_verdict": observed_task,
            "task_verdict_match": observed_task == expected_task,
            "false_supported": false_supported,
            "false_failed": false_failed,
        },
        "privacy": {
            "secret_required": False,
            "raw_private_material_stored": False,
            "absolute_path_stored": False,
            "reversible_private_identifier_stored": False,
        },
        "runtime": {"basis": "deterministic_case_unit", "units": 1},
        "claim_boundary": MVP_BOUNDARY,
    }
    if _contains_private_material(report):
        raise ValueError("private_or_absolute_path_material_in_mvp_report")
    return report


def build_mvp_reports(project_root: Path) -> list[dict[str, Any]]:
    contracts = load_mvp_contracts(project_root)
    reports: list[dict[str, Any]] = []
    with running_local_mcp_server(project_root):
        for contract in contracts:
            case_id = contract["case_id"]
            if case_id not in REAL_MCP_CASE_IDS:
                continue
            scenario = _scenario(contract)
            transport_result = asyncio.run(
                fetch_timeline_inputs(int(scenario["tool_limit"]))
            )
            events = _transform_real_events(case_id, transport_result["events"])
            reports.append(
                evaluate_mvp_case(contract, events, transport_result["transport"])
            )
    by_id = {contract["case_id"]: contract for contract in contracts}
    for case_id in EXPECTED_CASE_IDS:
        if case_id not in TOOL_FAILURE_CASE_IDS:
            continue
        events = _fault_events(case_id)
        reports.append(
            evaluate_mvp_case(
                by_id[case_id],
                events,
                _fault_transport(by_id[case_id], len(events)),
            )
        )
    report_by_id = {report["case_id"]: report for report in reports}
    if set(report_by_id) != set(EXPECTED_CASE_IDS):
        raise ValueError("mvp_report_set_incomplete")
    return [report_by_id[case_id] for case_id in EXPECTED_CASE_IDS]


def _regression_receipt(
    project_root: Path,
    identities: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    items = {}
    for item_id, (relative_path, expected) in identities.items():
        observed = _sha256_file(project_root / relative_path)
        items[item_id] = {
            "sha256": observed,
            "expected_sha256": expected,
            "identity_match": observed == expected,
        }
    return {
        "total": len(items),
        "identity_matches": sum(item["identity_match"] for item in items.values()),
        "items": items,
    }


def build_mvp_aggregate(
    reports: list[dict[str, Any]],
    project_root: Path,
) -> dict[str, Any]:
    claims = [report["timeline"][0] for report in reports]
    status_values = ("Supported", "Unknown", "Conflict")
    task_values = ("supported", "failed")
    d3_receipt = _regression_receipt(project_root, D3_REGRESSION_IDENTITIES)
    vs1_receipt = _regression_receipt(project_root, VS1_REGRESSION_IDENTITIES)
    privacy_leaks = sum(_contains_private_material(report) for report in reports)
    return {
        "schema_version": MVP_AGGREGATE_SCHEMA_VERSION,
        "mvp_id": MVP_ID,
        "case_ids": [report["case_id"] for report in reports],
        "counts": {
            "total": len(reports),
            **{
                f"claim_{status.lower()}": sum(
                    claim["status"] == status for claim in claims
                )
                for status in status_values
            },
            **{
                f"task_{value}": sum(
                    report["evaluation"]["observed_task_verdict"] == value
                    for report in reports
                )
                for value in task_values
            },
            "status_exact_match": sum(
                report["evaluation"]["status_exact_match"] for report in reports
            ),
            "task_verdict_match": sum(
                report["evaluation"]["task_verdict_match"] for report in reports
            ),
            "missing_requirements_match": sum(
                report["evaluation"]["missing_requirements_match"]
                for report in reports
            ),
            "contradictions_match": sum(
                report["evaluation"]["contradictions_match"] for report in reports
            ),
            "policy_violations": sum(
                report["policy"]["observed"] == "violation" for report in reports
            ),
            "tool_failure_correct_safe_behavior": sum(
                report["tool_behavior"]["correct_safe_behavior"] is True
                for report in reports
            ),
            "real_mcp_transport": sum(
                report["transport"]["real_transport"] is True for report in reports
            ),
            "false_supported": sum(
                report["evaluation"]["false_supported"] for report in reports
            ),
            "false_failed": sum(
                report["evaluation"]["false_failed"] for report in reports
            ),
            "non_supported_story_fact_leaks": sum(
                report["story"]["non_supported_fact_emitted"] for report in reports
            ),
            "privacy_or_absolute_path_leaks": privacy_leaks,
        },
        "report_sha256": {
            report["case_id"]: sha256_text(canonical_json(report)) for report in reports
        },
        "report_hash_basis": CANONICAL_JSON_HASH_BASIS,
        "d3_regression": d3_receipt,
        "vs1_regression": vs1_receipt,
        "combined_receipt": {
            "top1_cases": len(reports),
            "d3_cases": d3_receipt["total"],
            "total": len(reports) + d3_receipt["total"],
            "reported_in_separate_sections": True,
        },
        "runtime": {
            "basis": "deterministic_case_unit",
            "per_case_units": {report["case_id"]: 1 for report in reports},
            "total_units": len(reports),
        },
        "claim_boundary": MVP_BOUNDARY,
    }


def readable_case_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Return the user-facing model consumed by the Streamlit review surface."""

    claim = report["timeline"][0]
    status_explanations = {
        "Supported": "必要证据完整且没有实质冲突。",
        "Unknown": "必要证据不足，系统保留未知而不补写事实。",
        "Conflict": "支持与冲突证据并存，系统等待人工核验而不静默选边。",
    }
    return {
        "case_id": report["case_id"],
        "family": report["family"],
        "statement": claim["statement"],
        "status": claim["status"],
        "status_explanation": status_explanations[claim["status"]],
        "supporting": report["evidence_review"]["supporting_pointers"],
        "contradicting": report["evidence_review"]["contradicting_pointers"],
        "missing": report["evidence_review"]["missing_requirements"],
        "policy_status": report["policy"]["observed"],
        "policy_violations": report["policy"]["violations"],
        "task_verdict": report["evaluation"]["observed_task_verdict"],
        "tool_fault": report["tool_behavior"]["fault"],
        "story_eligible": report["story"]["eligible"],
        "story_facts": report["story"]["factual_inputs"],
    }
