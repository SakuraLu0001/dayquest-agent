"""Day 3 branch-breadth scenarios built only from existing DayQuest semantics."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .agent import run_agent
from .evaluation import (
    CANONICAL_JSON_HASH_BASIS,
    DeterministicClock,
    JUDGMENTS,
    canonical_json,
    evaluate_case,
    sha256_text,
)
from .nexla_client import NexlaClientError, NexlaDiagnostics


BRANCH_AGGREGATE_SCHEMA_VERSION = "dayquest.branch_breadth_aggregate.v1"
BRANCH_SLICE_LABEL = "Day 3 branch-breadth development slice"
BRANCH_CLAIM_BOUNDARY = (
    "Includes a deliberate harness self-test fault fixture; it is not a product failure-rate, "
    "final benchmark, or statistical performance claim."
)


class FailingNexlaFixtureClient:
    """No-network fake client that enters the existing categorized fallback branch."""

    configured = True
    configuration_error = None
    config = SimpleNamespace(nexset_id="synthetic-failure-fixture")

    def fetch_normalized_events(self) -> None:
        raise NexlaClientError(
            "authentication_or_expired_token",
            NexlaDiagnostics(http_status=401, latency_ms=1),
        )


def _recovery_observed(state: Any, contract: dict[str, Any]) -> bool:
    if not contract["expected_recovery_success"]:
        return False
    status = state.nexla_status
    return bool(
        status["attempted"]
        and status["fallback_used"]
        and not status["connected"]
        and status["error_type"] == "authentication_or_expired_token"
        and {"calendar", "transactions", "emails"}.issubset(state.queried_sources)
        and state.evaluation.get("passed") is True
    )


def _enrich_report(
    report: dict[str, Any],
    contract: dict[str, Any],
    state: Any,
) -> dict[str, Any]:
    recovery_observed = _recovery_observed(state, contract)
    unsafe_continuation = bool(
        report["policy"]["observed"] == "violation"
        and report["terminal"]["observed_class"] == "success"
    )
    report.update(
        {
            "slice_label": BRANCH_SLICE_LABEL,
            "test_report_identity": "pytest:tests/test_branch_breadth_slice.py",
            "fixture_kind": contract["fixture_kind"],
            "recovery": {
                "expected": contract["expected_recovery_success"],
                "observed": recovery_observed,
                "provider": "nexla" if contract["expected_recovery_success"] else None,
                "error_type": (
                    state.nexla_status["error_type"]
                    if contract["expected_recovery_success"]
                    else None
                ),
            },
            "unsafe_continuation": unsafe_continuation,
            "expected_unsafe_continuation": contract["expected_unsafe_continuation"],
            "claim_boundary": BRANCH_CLAIM_BOUNDARY,
        }
    )
    return report


def execute_branch_case(contract: dict[str, Any], project_root: Path) -> dict[str, Any]:
    scenario_id = contract["scenario"]["id"]
    data_dir = project_root / "data"
    if scenario_id == "nexla_categorized_failure_local_recovery":
        state = run_agent(
            data_dir,
            nexla_client=FailingNexlaFixtureClient(),  # type: ignore[arg-type]
            run_id=contract["run_id"],
            trace_clock=DeterministicClock(),
        )
        report = evaluate_case(contract, state)
    elif scenario_id == "maximum_iteration_safe_stop":
        state = run_agent(
            data_dir,
            max_iterations=1,
            run_id=contract["run_id"],
            trace_clock=DeterministicClock(),
        )
        report = evaluate_case(contract, state)
    elif scenario_id == "unexpected_retry_policy_counterexample":
        state = run_agent(
            data_dir,
            run_id=contract["run_id"],
            trace_clock=DeterministicClock(),
        )
        trace_fixture = [event.to_dict() for event in state.structured_trace]
        trace_fixture[0]["retry_attempt"] = 1
        report = evaluate_case(contract, state, trace_override=trace_fixture)
    else:
        raise ValueError(f"unsupported_branch_scenario:{scenario_id}")
    return _enrich_report(report, contract, state)


def build_branch_breadth_aggregate(reports: list[dict[str, Any]]) -> dict[str, Any]:
    judgment_counts = {
        value: sum(report["judgment"] == value for report in reports)
        for value in sorted(JUDGMENTS)
    }
    per_case_runtime = {
        report["case_id"]: report["runtime"]["milliseconds"] for report in reports
    }
    return {
        "schema_version": BRANCH_AGGREGATE_SCHEMA_VERSION,
        "slice_label": BRANCH_SLICE_LABEL,
        "scope": "five_case_deterministic_local_branch_breadth_slice",
        "case_ids": [report["case_id"] for report in reports],
        "counts": {
            "total": len(reports),
            **judgment_counts,
            "expected_outcome_matches": sum(
                report["terminal"]["outcome_match"] for report in reports
            ),
            "correct_safe_behavior": sum(
                report["correct_safe_behavior"] for report in reports
            ),
            "recovery_success": sum(
                report.get("recovery", {}).get("observed", False) for report in reports
            ),
            "unsafe_continuation": sum(
                report.get("unsafe_continuation", False) for report in reports
            ),
            "policy_violations": sum(
                bool(report["policy"]["violations"]) for report in reports
            ),
            "checker_false_pass": sum(
                report["judgment"] == "supported"
                and report["expected_judgment"] != "supported"
                for report in reports
            ),
            "checker_false_fail": sum(
                report["judgment"] != "supported"
                and report["expected_judgment"] == "supported"
                for report in reports
            ),
        },
        "runtime": {
            "basis": "deterministic_trace_latency_sum",
            "per_case_milliseconds": per_case_runtime,
            "total_milliseconds": sum(per_case_runtime.values()),
        },
        "report_sha256": {
            report["case_id"]: sha256_text(canonical_json(report)) for report in reports
        },
        "report_hash_basis": CANONICAL_JSON_HASH_BASIS,
        "claim_boundary": BRANCH_CLAIM_BOUNDARY,
    }
