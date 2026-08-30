from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from dayquest.branch_breadth import (
    BRANCH_CLAIM_BOUNDARY,
    BRANCH_SLICE_LABEL,
    build_branch_breadth_aggregate,
    execute_branch_case,
)
from dayquest.evaluation import CANONICAL_JSON_HASH_BASIS, canonical_json, sha256_text
from scripts.run_branch_breadth_slice import (
    AGGREGATE_OUTPUT,
    CONTRACT_ROOT,
    DAY2_ROOT,
    build_outputs,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ABSOLUTE_WINDOWS_PATH = re.compile(r"\b[A-Za-z]:[\\/]")
ACCEPTED_DAY2_IDENTITIES = {
    "aggregate": "11478F89E8DE970BF581FBC71EDFB63269165142E4088D03AE88BEAF3B1DDD5B",
    "DQ-EVAL-BASELINE-001": "881655C9D85CC8552414E490E377EA75E42270F48645D8C4014B700333C73824",
    "DQ-EVAL-LOCAL-ERROR-001": "0EB9A0824A8BBCD0FEB1D12BD775E0C62BF2FA841BD46857D2D896AAA75C8C16",
}


def _contracts() -> list[dict[str, object]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CONTRACT_ROOT.glob("*.json"))
    ]


def _new_reports() -> list[dict[str, object]]:
    return [execute_branch_case(contract, PROJECT_ROOT) for contract in _contracts()]


def _all_reports() -> list[dict[str, object]]:
    day2 = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((DAY2_ROOT / "reports").glob("*.json"))
    ]
    return sorted([*day2, *_new_reports()], key=lambda report: report["case_id"])


def test_day3_contracts_are_the_exact_minimum_branch_set() -> None:
    contracts = _contracts()

    assert [contract["case_id"] for contract in contracts] == [
        "DQ-EVAL-MAX-ITERATION-001",
        "DQ-EVAL-NEXLA-RECOVERY-001",
        "DQ-EVAL-POLICY-COUNTEREXAMPLE-001",
    ]
    assert all(contract["schema_version"] == "dayquest.eval_case.v1" for contract in contracts)
    assert all(contract["required_trace_evidence"] for contract in contracts)


def test_nexla_failure_recovers_through_existing_local_fallback() -> None:
    contract = _contracts()[1]
    report = execute_branch_case(contract, PROJECT_ROOT)

    assert report["judgment"] == "supported"
    assert report["slice_label"] == BRANCH_SLICE_LABEL
    assert report["test_report_identity"] == "pytest:tests/test_branch_breadth_slice.py"
    assert report["terminal"]["observed_class"] == "success"
    assert report["recovery"] == {
        "expected": True,
        "observed": True,
        "provider": "nexla",
        "error_type": "authentication_or_expired_token",
    }
    assert report["policy"]["observed"] == "compliant"


def test_max_iteration_uses_existing_safe_stop_terminal() -> None:
    contract = _contracts()[0]
    report = execute_branch_case(contract, PROJECT_ROOT)

    assert report["judgment"] == "supported"
    assert report["terminal"]["observed_class"] == "safe_stop_max_iterations"
    assert [event["tool"] for event in report["trace_evidence"]] == ["READ_CALENDAR"]


def test_policy_counterexample_is_failed_not_supported() -> None:
    contract = _contracts()[2]
    report = execute_branch_case(contract, PROJECT_ROOT)

    assert report["fixture_kind"] == "harness_self_test_fault_fixture"
    assert report["terminal"]["claim_support"] == "supported"
    assert report["policy"]["observed"] == "violation"
    assert report["policy"]["violations"] == ["unexpected_retry"]
    assert report["unsafe_continuation"] is True
    assert report["judgment"] == "failed"
    assert report["claim_boundary"] == BRANCH_CLAIM_BOUNDARY


def test_five_case_aggregate_reconciles_branch_metrics() -> None:
    reports = _all_reports()
    aggregate = build_branch_breadth_aggregate(reports)

    assert aggregate["slice_label"] == BRANCH_SLICE_LABEL
    assert aggregate["counts"] == {
        "total": 5,
        "failed": 1,
        "supported": 4,
        "unknown": 0,
        "expected_outcome_matches": 5,
        "correct_safe_behavior": 4,
        "recovery_success": 1,
        "unsafe_continuation": 1,
        "policy_violations": 1,
        "checker_false_pass": 0,
        "checker_false_fail": 0,
    }
    assert aggregate["runtime"]["total_milliseconds"] == 13
    assert aggregate["report_hash_basis"] == CANONICAL_JSON_HASH_BASIS
    assert aggregate["claim_boundary"] == BRANCH_CLAIM_BOUNDARY


def test_accepted_day2_artifact_identities_are_unchanged() -> None:
    day2_aggregate = DAY2_ROOT / "aggregate.json"
    day2_reports = DAY2_ROOT / "reports"

    assert hashlib.sha256(day2_aggregate.read_bytes()).hexdigest().upper() == ACCEPTED_DAY2_IDENTITIES["aggregate"]
    for case_id in ("DQ-EVAL-BASELINE-001", "DQ-EVAL-LOCAL-ERROR-001"):
        report_path = day2_reports / f"{case_id}.json"
        assert hashlib.sha256(report_path.read_bytes()).hexdigest().upper() == ACCEPTED_DAY2_IDENTITIES[case_id]


def test_branch_outputs_are_byte_stable_and_hash_basis_resolves() -> None:
    first = build_outputs()
    second = build_outputs()

    assert first == second
    assert all(path.read_text(encoding="utf-8") == content for path, content in first.items())
    aggregate = json.loads(first[AGGREGATE_OUTPUT])
    for report in _new_reports():
        assert report["case_contract_hash_basis"] == CANONICAL_JSON_HASH_BASIS
        assert report["case_contract_sha256"] == sha256_text(
            canonical_json(next(contract for contract in _contracts() if contract["case_id"] == report["case_id"]))
        )
    assert aggregate["report_hash_basis"] == CANONICAL_JSON_HASH_BASIS


def test_branch_artifacts_contain_no_private_text_or_absolute_paths() -> None:
    serialized = "".join(build_outputs().values())

    assert not ABSOLUTE_WINDOWS_PATH.search(serialized)
    assert "demo.user@example.com" not in serialized
    assert "DQ-77102" not in serialized
    assert "Bearer " not in serialized
