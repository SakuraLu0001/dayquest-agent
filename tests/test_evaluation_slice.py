from __future__ import annotations

import json
import re
from pathlib import Path

from dayquest.agent import run_agent
from dayquest.evaluation import (
    CASE_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    SLICE_LABEL,
    DeterministicClock,
    build_aggregate,
    evaluate_case,
    execute_case,
)
from scripts.run_evaluation_slice import AGGREGATE_OUTPUT, CONTRACT_ROOT, build_outputs


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_DATA = PROJECT_ROOT / "data"
ABSOLUTE_WINDOWS_PATH = re.compile(r"\b[A-Za-z]:[\\/]")


def _contracts() -> list[dict[str, object]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(CONTRACT_ROOT.glob("*.json"))]


def _baseline_contract() -> dict[str, object]:
    return _contracts()[0]


def _baseline_state():
    contract = _baseline_contract()
    return run_agent(
        PROJECT_DATA,
        run_id=contract["run_id"],
        trace_clock=DeterministicClock(),
    )


def test_day2_case_contracts_are_versioned_and_exact() -> None:
    contracts = _contracts()

    assert [contract["case_id"] for contract in contracts] == [
        "DQ-EVAL-BASELINE-001",
        "DQ-EVAL-LOCAL-ERROR-001",
    ]
    assert all(contract["schema_version"] == CASE_SCHEMA_VERSION for contract in contracts)
    assert all(contract["expected_judgment"] == "supported" for contract in contracts)
    assert all(contract["required_trace_evidence"] for contract in contracts)
    assert all(contract["expected_policy_result"] == "compliant" for contract in contracts)


def test_baseline_case_is_supported_by_exact_trace_and_terminal() -> None:
    contract = _baseline_contract()
    report = execute_case(contract, PROJECT_ROOT)

    assert report["schema_version"] == REPORT_SCHEMA_VERSION
    assert report["slice_label"] == SLICE_LABEL
    assert report["record_validity"]["observed"] == "valid"
    assert report["policy"]["observed"] == "compliant"
    assert report["terminal"] == {
        "expected_class": "success",
        "observed_class": "success",
        "outcome_match": True,
        "claim_support": "supported",
    }
    assert report["judgment"] == "supported"
    assert set(report["evidence"]["pointers"].values()) == {
        event["step_id"] for event in report["trace_evidence"]
    }


def test_local_error_case_uses_existing_safe_stop_semantics() -> None:
    contract = _contracts()[1]
    report = execute_case(contract, PROJECT_ROOT)

    assert report["terminal"]["observed_class"] == "safe_stop_insufficient_evidence"
    assert report["terminal"]["claim_support"] == "supported"
    assert report["policy"]["violations"] == []
    assert report["judgment"] == "supported"
    assert report["evidence"]["pointers"] == {
        "calendar_unavailable": "dq-eval-local-error-001-v1:step-001",
        "transactions_continue": "dq-eval-local-error-001-v1:step-002",
        "emails_continue": "dq-eval-local-error-001-v1:step-003",
    }
    assert report["trace_evidence"][0]["error_type"] == "data_load_error"
    assert report["trace_evidence"][0]["result"] == "unavailable"


def test_missing_required_evidence_is_unknown_not_false_pass() -> None:
    contract = _baseline_contract()
    state = _baseline_state()
    incomplete_trace = state.structured_trace[:-1]

    report = evaluate_case(contract, state, trace_override=incomplete_trace)

    assert report["evidence"]["missing_required"] == ["emails_loaded"]
    assert report["terminal"]["claim_support"] == "unknown"
    assert report["judgment"] == "unknown"


def test_contradicted_required_evidence_is_failed_not_false_pass() -> None:
    contract = _baseline_contract()
    state = _baseline_state()
    contradicted_trace = [event.to_dict() for event in state.structured_trace]
    contradicted_trace[0]["status"] = "failed"

    report = evaluate_case(contract, state, trace_override=contradicted_trace)

    assert report["evidence"]["contradicted_required"] == ["calendar_loaded"]
    assert report["terminal"]["claim_support"] == "failed"
    assert report["judgment"] == "failed"


def test_aggregate_reconciles_named_reports_and_exact_counts() -> None:
    reports = [execute_case(contract, PROJECT_ROOT) for contract in _contracts()]
    aggregate = build_aggregate(reports)

    assert aggregate["slice_label"] == SLICE_LABEL
    assert aggregate["case_ids"] == ["DQ-EVAL-BASELINE-001", "DQ-EVAL-LOCAL-ERROR-001"]
    assert aggregate["counts"] == {
        "total": 2,
        "failed": 0,
        "supported": 2,
        "unknown": 0,
        "expected_outcome_matches": 2,
        "correct_safe_behavior": 2,
        "policy_violations": 0,
        "checker_false_pass": 0,
        "checker_false_fail": 0,
    }
    assert aggregate["runtime"]["per_case_milliseconds"] == {
        "DQ-EVAL-BASELINE-001": 3,
        "DQ-EVAL-LOCAL-ERROR-001": 3,
    }
    assert aggregate["runtime"]["total_milliseconds"] == 6


def test_committed_reports_and_aggregate_are_byte_stable() -> None:
    first = build_outputs()
    second = build_outputs()

    assert first == second
    assert all(path.read_text(encoding="utf-8") == content for path, content in first.items())
    assert AGGREGATE_OUTPUT in first


def test_evaluation_artifacts_contain_no_private_text_or_absolute_paths() -> None:
    outputs = build_outputs()
    serialized = "".join(outputs.values())

    assert not ABSOLUTE_WINDOWS_PATH.search(serialized)
    assert "demo.user@example.com" not in serialized
    assert "DQ-77102" not in serialized
    assert "Bearer " not in serialized
