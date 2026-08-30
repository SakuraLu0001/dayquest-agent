from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from dayquest.evaluation import canonical_json
from dayquest.timeline_mvp import (
    EXPECTED_CASE_IDS,
    TOOL_FAILURE_CASE_IDS,
    build_mvp_aggregate,
    build_mvp_reports,
    readable_case_summary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "evaluation" / "top1" / "mvp"
REPORT_ROOT = ARTIFACT_ROOT / "reports"
PRIVATE_OR_PATH = re.compile(
    r"(?:\b[A-Za-z]:[\\/]|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|\bsk-[A-Za-z0-9._-]{8,})",
    re.IGNORECASE,
)


@pytest.fixture(scope="module")
def mvp_result() -> tuple[list[dict], dict]:
    reports = build_mvp_reports(PROJECT_ROOT)
    return reports, build_mvp_aggregate(reports, PROJECT_ROOT)


def _by_id(reports: list[dict]) -> dict[str, dict]:
    return {report["case_id"]: report for report in reports}


def test_exact_twelve_case_product_matrix(mvp_result):
    reports, aggregate = mvp_result
    assert [report["case_id"] for report in reports] == EXPECTED_CASE_IDS
    assert aggregate["case_ids"] == EXPECTED_CASE_IDS


def test_aggregate_closes_status_and_policy_counts(mvp_result):
    _, aggregate = mvp_result
    assert aggregate["counts"] == {
        "total": 12,
        "claim_supported": 3,
        "claim_unknown": 7,
        "claim_conflict": 2,
        "task_supported": 10,
        "task_failed": 2,
        "status_exact_match": 12,
        "task_verdict_match": 12,
        "missing_requirements_match": 12,
        "contradictions_match": 12,
        "policy_violations": 2,
        "tool_failure_correct_safe_behavior": 4,
        "real_mcp_transport": 8,
        "false_supported": 0,
        "false_failed": 0,
        "non_supported_story_fact_leaks": 0,
        "privacy_or_absolute_path_leaks": 0,
    }


def test_conflicts_expose_both_evidence_roles(mvp_result):
    reports, _ = mvp_result
    for case_id in ("DQ-TOP1-CONFLICT-001", "DQ-TOP1-CONFLICT-002"):
        report = _by_id(reports)[case_id]
        assert report["timeline"][0]["status"] == "Conflict"
        assert report["evidence_review"]["supporting_pointers"]
        assert report["evidence_review"]["contradicting_pointers"]
        assert report["timeline"][0]["contradictions"]


def test_missing_cases_name_required_evidence(mvp_result):
    reports, _ = mvp_result
    by_id = _by_id(reports)
    assert by_id["DQ-TOP1-MISSING-001"]["evidence_review"]["missing_requirements"] == ["calendar_language_exam"]
    assert by_id["DQ-TOP1-MISSING-002"]["evidence_review"]["missing_requirements"] == ["calendar_hackathon_evening"]


def test_policy_verdict_is_separate_from_claim_status(mvp_result):
    reports, _ = mvp_result
    by_id = _by_id(reports)
    assert by_id["DQ-TOP1-POLICY-001"]["timeline"][0]["status"] == "Supported"
    assert by_id["DQ-TOP1-POLICY-001"]["policy"]["observed"] == "violation"
    assert by_id["DQ-TOP1-POLICY-001"]["evaluation"]["observed_task_verdict"] == "failed"
    assert by_id["DQ-TOP1-POLICY-002"]["timeline"][0]["status"] == "Unknown"


def test_tool_faults_stop_or_degrade_conservatively(mvp_result):
    reports, _ = mvp_result
    by_id = _by_id(reports)
    for case_id in TOOL_FAILURE_CASE_IDS:
        report = by_id[case_id]
        assert report["timeline"][0]["status"] == "Unknown"
        assert report["tool_behavior"]["correct_safe_behavior"] is True
        assert report["tool_behavior"]["retry_attempts"] == 0
        assert report["tool_behavior"]["terminal"].startswith("safe_")


def test_story_consumes_only_supported_compliant_claims(mvp_result):
    reports, _ = mvp_result
    for report in reports:
        should_be_eligible = (
            report["timeline"][0]["status"] == "Supported"
            and report["policy"]["observed"] == "compliant"
        )
        assert report["story"]["eligible"] is should_be_eligible
        assert bool(report["story"]["factual_inputs"]) is should_be_eligible


def test_reports_are_privacy_safe_and_path_free(mvp_result):
    reports, _ = mvp_result
    for report in reports:
        assert not PRIVATE_OR_PATH.search(canonical_json(report))
        assert report["privacy"] == {
            "secret_required": False,
            "raw_private_material_stored": False,
            "absolute_path_stored": False,
            "reversible_private_identifier_stored": False,
        }


def test_committed_mvp_outputs_are_byte_stable(mvp_result):
    reports, aggregate = mvp_result
    for report in reports:
        path = REPORT_ROOT / f"{report['case_id']}.json"
        assert path.read_text(encoding="utf-8") == canonical_json(report)
    assert (ARTIFACT_ROOT / "aggregate.json").read_text("utf-8") == canonical_json(aggregate)


def test_previous_d3_and_vs1_identities_remain_closed(mvp_result):
    _, aggregate = mvp_result
    assert aggregate["d3_regression"]["identity_matches"] == 5
    assert aggregate["vs1_regression"]["identity_matches"] == 3
    assert aggregate["combined_receipt"] == {
        "top1_cases": 12,
        "d3_cases": 5,
        "total": 17,
        "reported_in_separate_sections": True,
    }


def test_existing_vs1_generator_still_matches_committed_bytes():
    script_path = PROJECT_ROOT / "scripts" / "run_timeline_slice.py"
    spec = importlib.util.spec_from_file_location("run_timeline_slice_regression", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for path, content in module.build_outputs().items():
        assert path.read_text(encoding="utf-8") == content


def test_readable_review_model_avoids_raw_payload(mvp_result):
    reports, _ = mvp_result
    view = readable_case_summary(_by_id(reports)["DQ-TOP1-CONFLICT-001"])
    assert view["status"] == "Conflict"
    assert "冲突" in view["status_explanation"]
    assert view["supporting"] and view["contradicting"]
    assert set(view) == {
        "case_id", "family", "statement", "status", "status_explanation",
        "supporting", "contradicting", "missing", "policy_status",
        "policy_violations", "task_verdict", "tool_fault", "story_eligible",
        "story_facts",
    }


def test_all_contracts_and_artifacts_are_json_parseable():
    for path in (ARTIFACT_ROOT / "contracts").glob("*.json"):
        json.loads(path.read_text("utf-8"))
    for path in (ARTIFACT_ROOT / "reports").glob("*.json"):
        json.loads(path.read_text("utf-8"))
    json.loads((ARTIFACT_ROOT / "aggregate.json").read_text("utf-8"))
