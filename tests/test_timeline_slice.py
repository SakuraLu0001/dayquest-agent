from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from dayquest.evaluation import canonical_json
from scripts.run_timeline_slice import (
    AGGREGATE_OUTPUT,
    CONTRACT_ROOT,
    EXPECTED_CASE_IDS,
    PROJECT_ROOT,
    REPORT_ROOT,
    build_outputs,
)


ACCEPTED_D3_IDENTITIES = {
    "artifacts/evaluation/day2/reports/DQ-EVAL-BASELINE-001.json": (
        "881655c9d85cc8552414e490e377ea75e42270f48645d8c4014b700333c73824"
    ),
    "artifacts/evaluation/day2/reports/DQ-EVAL-LOCAL-ERROR-001.json": (
        "0eb9a0824a8bbcd0feb1d12bd775e0c62bf2fa841bd46857d2d896aaa75c8c16"
    ),
    "artifacts/evaluation/day3/aggregate.json": (
        "35f693767994997d5aa41cb5680d0a8856c8edf8f689ed215ddb1b272231262a"
    ),
}


@pytest.fixture(scope="module")
def generated_runs() -> tuple[dict[Path, str], dict[Path, str]]:
    return build_outputs(), build_outputs()


def _reports(outputs: dict[Path, str]) -> dict[str, dict[str, Any]]:
    return {
        case_id: json.loads(outputs[REPORT_ROOT / f"{case_id}.json"])
        for case_id in EXPECTED_CASE_IDS
    }


def test_contracts_are_exact_two_case_minimal_pair() -> None:
    contracts = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CONTRACT_ROOT.glob("*.json"))
    ]

    assert [contract["case_id"] for contract in contracts] == EXPECTED_CASE_IDS
    assert {contract["focal_claim"]["statement"] for contract in contracts} == {
        "A morning language certification exam occurred."
    }
    assert {contract["tool_limit"] for contract in contracts} == {2, 3}
    assert {contract["expected_claim_status"] for contract in contracts} == {
        "Supported",
        "Unknown",
    }


def test_positive_case_uses_real_mcp_and_complete_source_pointers(
    generated_runs: tuple[dict[Path, str], dict[Path, str]],
) -> None:
    generated_outputs = generated_runs[0]
    report = _reports(generated_outputs)["DQ-TOP1-POSITIVE-001"]
    claim = report["timeline"][0]

    assert report["transport"]["real_transport"] is True
    assert report["transport"]["transport"] == "streamable-http"
    assert report["transport"]["local_only"] is True
    assert claim["status"] == "Supported"
    assert {pointer["evidence_id"] for pointer in claim["source_pointers"]} == {
        "calendar_language_exam",
        "email_exam_confirmation",
    }
    assert claim["missing_required_evidence"] == []


def test_missing_case_is_unknown_and_never_false_supported(
    generated_runs: tuple[dict[Path, str], dict[Path, str]],
) -> None:
    generated_outputs = generated_runs[0]
    report = _reports(generated_outputs)["DQ-TOP1-MISSING-001"]
    claim = report["timeline"][0]

    assert report["transport"]["real_transport"] is True
    assert claim["status"] == "Unknown"
    assert claim["missing_required_evidence"] == ["calendar_language_exam"]
    assert report["evaluation"]["false_supported"] is False
    assert report["evaluation"]["missing_requirement_complete"] is True


def test_aggregate_closes_the_exact_vs1_evidence_gate(
    generated_runs: tuple[dict[Path, str], dict[Path, str]],
) -> None:
    generated_outputs = generated_runs[0]
    aggregate = json.loads(generated_outputs[AGGREGATE_OUTPUT])

    assert aggregate["case_ids"] == EXPECTED_CASE_IDS
    assert aggregate["counts"] == {
        "conflict_claims": 0,
        "false_supported": 0,
        "missing_requirement_complete": 1,
        "privacy_or_absolute_path_leaks": 0,
        "real_mcp_transport": 2,
        "source_pointer_complete": 1,
        "status_exact_match": 2,
        "supported_claims": 1,
        "task_verdict_match": 2,
        "total": 2,
        "unknown_claims": 1,
    }


def test_committed_artifacts_are_byte_stable_and_privacy_safe(
    generated_runs: tuple[dict[Path, str], dict[Path, str]],
) -> None:
    generated_outputs = generated_runs[0]
    forbidden = ("@", "bearer ", "sk-", "D:\\", "C:\\", "api_key", "token")
    for path, content in generated_outputs.items():
        assert path.read_text(encoding="utf-8") == content
        lowered = content.lower()
        assert not any(marker.lower() in lowered for marker in forbidden)
        assert canonical_json(json.loads(content)) == content


def test_provenance_identity_is_stable_across_process_restart_and_case_views(
    generated_runs: tuple[dict[Path, str], dict[Path, str]],
) -> None:
    first_reports = _reports(generated_runs[0])
    second_reports = _reports(generated_runs[1])

    def pointer(report: dict[str, Any], evidence_id: str) -> dict[str, str]:
        return next(
            item
            for item in report["timeline"][0]["source_pointers"]
            if item["evidence_id"] == evidence_id
        )

    positive_email = pointer(
        first_reports["DQ-TOP1-POSITIVE-001"], "email_exam_confirmation"
    )
    missing_email = pointer(
        first_reports["DQ-TOP1-MISSING-001"], "email_exam_confirmation"
    )
    restarted_email = pointer(
        second_reports["DQ-TOP1-POSITIVE-001"], "email_exam_confirmation"
    )

    assert canonical_json(positive_email) == canonical_json(missing_email)
    assert canonical_json(positive_email) == canonical_json(restarted_email)
    assert positive_email["identity_schema"] == "dayquest.safe_event_identity.v1"


def test_current_fixture_safe_identities_have_no_collision(
    generated_runs: tuple[dict[Path, str], dict[Path, str]],
) -> None:
    report = _reports(generated_runs[0])["DQ-TOP1-POSITIVE-001"]
    pointers = report["timeline"][0]["source_pointers"]

    assert len({pointer["safe_record_id"] for pointer in pointers}) == len(pointers)


def test_accepted_day2_and_day3_artifact_identities_are_unchanged() -> None:
    for relative_path, expected_sha256 in ACCEPTED_D3_IDENTITIES.items():
        actual = hashlib.sha256((PROJECT_ROOT / relative_path).read_bytes()).hexdigest()
        assert actual == expected_sha256
