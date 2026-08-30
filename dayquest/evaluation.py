"""Deterministic evaluation contracts and reports for DayQuest traces."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .agent import run_agent
from .models import AgentState
from .structured_trace import TRACE_SCHEMA_VERSION, ToolTraceEvent


CASE_SCHEMA_VERSION = "dayquest.eval_case.v1"
REPORT_SCHEMA_VERSION = "dayquest.eval_report.v1"
AGGREGATE_SCHEMA_VERSION = "dayquest.eval_aggregate.v1"
SLICE_LABEL = "Day 2 development slice"
CANONICAL_JSON_HASH_BASIS = (
    "SHA-256 of parsed JSON serialized as UTF-8 with ensure_ascii=false, "
    "indent=2, sort_keys=true, and one trailing LF newline"
)
JUDGMENTS = {"supported", "failed", "unknown"}
ALLOWED_TOOLS = {"READ_CALENDAR", "READ_TRANSACTIONS", "READ_EMAILS"}
_ABSOLUTE_WINDOWS_PATH = re.compile(r"\b[A-Za-z]:[\\/]")
_FORBIDDEN_TEXT = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?i)\b(?:bearer\s+|sk-)[A-Za-z0-9._-]{8,}"),
)


class DeterministicClock:
    """Return fixed 1 ms intervals for byte-stable development artifacts."""

    def __init__(self) -> None:
        self._tick = 0

    def __call__(self) -> float:
        self._tick += 1
        return self._tick / 1000


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest().upper()


def _contains_private_text(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_private_text(key) or _contains_private_text(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_private_text(item) for item in value)
    if not isinstance(value, str):
        return False
    return bool(_ABSOLUTE_WINDOWS_PATH.search(value) or any(pattern.search(value) for pattern in _FORBIDDEN_TEXT))


def _terminal_class(state: AgentState) -> str:
    if state.finished and state.evaluation.get("passed") is True:
        return "success"
    if state.finished and state.stop_reason.startswith("Stopped safely:"):
        return "safe_stop_insufficient_evidence"
    if state.finished and state.evaluation.get("passed") is False:
        return "safe_stop_evaluation_failed"
    if state.finished:
        return "safe_stop_other"
    return "unfinished"


def _record_validity(contract: dict[str, Any], trace: list[dict[str, Any]]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if contract.get("schema_version") != CASE_SCHEMA_VERSION:
        reasons.append("unsupported_case_schema")
    if not contract.get("case_id") or not contract.get("run_id"):
        reasons.append("missing_case_identity")
    if not isinstance(contract.get("required_trace_evidence"), list):
        reasons.append("required_trace_evidence_not_list")
    step_ids: list[str] = []
    for event in trace:
        try:
            ToolTraceEvent(**event)
        except (TypeError, ValueError):
            reasons.append("invalid_trace_event")
        if event.get("schema_version") != TRACE_SCHEMA_VERSION:
            reasons.append("unsupported_trace_schema")
        if event.get("run_id") != contract.get("run_id"):
            reasons.append("trace_run_identity_mismatch")
        step_id = event.get("step_id")
        if not isinstance(step_id, str) or not step_id.startswith(f"{contract.get('run_id')}:step-"):
            reasons.append("unstable_step_identity")
        elif step_id in step_ids:
            reasons.append("duplicate_step_identity")
        else:
            step_ids.append(step_id)
    if not trace:
        reasons.append("trace_is_empty")
    return ("valid" if not reasons else "invalid", sorted(set(reasons)))


def _policy_result(contract: dict[str, Any], trace: list[dict[str, Any]]) -> tuple[str, list[str]]:
    violations: list[str] = []
    for event in trace:
        if event.get("tool") not in ALLOWED_TOOLS:
            violations.append("forbidden_tool_action")
        if event.get("retry_attempt") != 0:
            violations.append("unexpected_retry")
        if _contains_private_text(event):
            violations.append("private_or_absolute_path_material")
    return ("compliant" if not violations else "violation", sorted(set(violations)))


def _match_required_evidence(
    contract: dict[str, Any], trace: list[dict[str, Any]]
) -> tuple[dict[str, str], list[str], list[str]]:
    pointers: dict[str, str] = {}
    missing: list[str] = []
    contradicted: list[str] = []
    for requirement in contract["required_trace_evidence"]:
        evidence_id = requirement["evidence_id"]
        same_tool = [event for event in trace if event.get("tool") == requirement["tool"]]
        exact = [
            event
            for event in same_tool
            if event.get("status") == requirement["status"]
            and event.get("error_type") == requirement.get("error_type")
            and event.get("output_summary", {}).get("result") == requirement["result"]
        ]
        if exact:
            pointers[evidence_id] = exact[0]["step_id"]
        elif same_tool:
            contradicted.append(evidence_id)
        else:
            missing.append(evidence_id)
    return pointers, missing, contradicted


def evaluate_case(
    contract: dict[str, Any],
    state: AgentState,
    *,
    trace_override: Iterable[ToolTraceEvent | dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate one run without changing application behavior or using model output."""
    source_trace = list(trace_override) if trace_override is not None else list(state.structured_trace)
    trace = [event.to_dict() if isinstance(event, ToolTraceEvent) else dict(event) for event in source_trace]
    record_result, record_reasons = _record_validity(contract, trace)
    observed_policy, policy_violations = _policy_result(contract, trace)
    pointers, missing, contradicted = _match_required_evidence(contract, trace)
    observed_terminal = _terminal_class(state)
    expected_terminal = contract["expected_terminal_class"]
    terminal_match = observed_terminal == expected_terminal

    if contradicted or not terminal_match:
        claim_support = "failed"
        reason_code = "required_evidence_or_terminal_contradicted"
    elif missing or record_result == "invalid":
        claim_support = "unknown"
        reason_code = "required_evidence_missing_or_record_invalid"
    else:
        claim_support = "supported"
        reason_code = "terminal_and_required_evidence_supported"

    if record_result == "invalid" or missing:
        overall = "unknown"
    elif contradicted or not terminal_match or observed_policy != contract["expected_policy_result"]:
        overall = "failed"
    else:
        overall = "supported"
    if overall not in JUDGMENTS:
        raise AssertionError("invalid_judgment")

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "slice_label": SLICE_LABEL,
        "case_id": contract["case_id"],
        "case_contract_schema_version": contract["schema_version"],
        "case_contract_sha256": sha256_text(canonical_json(contract)),
        "case_contract_hash_basis": CANONICAL_JSON_HASH_BASIS,
        "run_id": contract["run_id"],
        "goal": contract["goal"],
        "scenario_id": contract["scenario"]["id"],
        "fault": contract["scenario"]["fault"],
        "record_validity": {"observed": record_result, "reasons": record_reasons},
        "policy": {
            "expected": contract["expected_policy_result"],
            "observed": observed_policy,
            "violations": policy_violations,
        },
        "terminal": {
            "expected_class": expected_terminal,
            "observed_class": observed_terminal,
            "outcome_match": terminal_match,
            "claim_support": claim_support,
        },
        "evidence": {
            "pointers": pointers,
            "missing_required": missing,
            "contradicted_required": contradicted,
        },
        "trace_evidence": [
            {
                "schema_version": event["schema_version"],
                "run_id": event["run_id"],
                "step_id": event["step_id"],
                "tool": event["tool"],
                "status": event["status"],
                "error_type": event["error_type"],
                "result": event["output_summary"]["result"],
                "latency_ms": event["latency_ms"],
                "retry_attempt": event["retry_attempt"],
            }
            for event in trace
        ],
        "judgment": overall,
        "expected_judgment": contract["expected_judgment"],
        "reason_code": reason_code,
        "correct_safe_behavior": terminal_match and observed_policy == "compliant",
        "runtime": {
            "basis": "deterministic_trace_latency_sum",
            "milliseconds": sum(int(event["latency_ms"]) for event in trace),
        },
        "test_report_identity": "pytest:tests/test_evaluation_slice.py",
    }


def execute_case(contract: dict[str, Any], project_root: Path) -> dict[str, Any]:
    scenario_id = contract["scenario"]["id"]
    if scenario_id == "synthetic_no_key_success":
        state = run_agent(
            project_root / "data",
            run_id=contract["run_id"],
            trace_clock=DeterministicClock(),
        )
    elif scenario_id == "missing_calendar_local_data_load_error":
        with tempfile.TemporaryDirectory(prefix="dayquest-eval-") as temp_dir:
            scenario_dir = Path(temp_dir)
            shutil.copy2(project_root / "data" / "transactions.csv", scenario_dir / "transactions.csv")
            shutil.copy2(project_root / "data" / "emails.json", scenario_dir / "emails.json")
            state = run_agent(
                scenario_dir,
                run_id=contract["run_id"],
                trace_clock=DeterministicClock(),
            )
    else:
        raise ValueError(f"unsupported_scenario:{scenario_id}")
    return evaluate_case(contract, state)


def build_aggregate(reports: list[dict[str, Any]]) -> dict[str, Any]:
    judgment_counts = {value: sum(report["judgment"] == value for report in reports) for value in sorted(JUDGMENTS)}
    per_case_runtime = {report["case_id"]: report["runtime"]["milliseconds"] for report in reports}
    report_sha256 = {report["case_id"]: sha256_text(canonical_json(report)) for report in reports}
    return {
        "schema_version": AGGREGATE_SCHEMA_VERSION,
        "slice_label": SLICE_LABEL,
        "scope": "two_case_deterministic_local_development_slice",
        "case_ids": [report["case_id"] for report in reports],
        "counts": {
            "total": len(reports),
            **judgment_counts,
            "expected_outcome_matches": sum(report["terminal"]["outcome_match"] for report in reports),
            "correct_safe_behavior": sum(report["correct_safe_behavior"] for report in reports),
            "policy_violations": sum(bool(report["policy"]["violations"]) for report in reports),
            "checker_false_pass": sum(
                report["judgment"] == "supported" and report["expected_judgment"] != "supported"
                for report in reports
            ),
            "checker_false_fail": sum(
                report["judgment"] != "supported" and report["expected_judgment"] == "supported"
                for report in reports
            ),
        },
        "runtime": {
            "basis": "deterministic_trace_latency_sum",
            "per_case_milliseconds": per_case_runtime,
            "total_milliseconds": sum(per_case_runtime.values()),
        },
        "report_sha256": report_sha256,
        "report_hash_basis": CANONICAL_JSON_HASH_BASIS,
        "claim_boundary": "Not a final benchmark or statistical performance claim.",
    }
