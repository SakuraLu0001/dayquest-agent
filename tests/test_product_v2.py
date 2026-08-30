from __future__ import annotations

import json
import re
from pathlib import Path

from dayquest.evaluation import canonical_json
from dayquest.product_v2 import (
    HYPOTHETICAL_IDENTITY_SCHEMA,
    build_product_v2,
    product_v2_identity,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "artifacts" / "product_v2" / "replay_demo.json"
PRIVATE_OR_PATH = re.compile(
    r"(?:\b[A-Za-z]:[\\/]|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|\bsk-[A-Za-z0-9._-]{8,})",
    re.IGNORECASE,
)


def _replays():
    artifact = build_product_v2(PROJECT_ROOT)
    return {item["intervention_id"]: item for item in artifact["replays"]}


def test_product_v2_has_exact_three_domain_replays():
    artifact = build_product_v2(PROJECT_ROOT)
    assert artifact["transition_counts"] == {
        "Supported->Unknown": 1,
        "Unknown->Supported": 1,
        "Conflict->Unknown": 1,
    }
    assert len(artifact["replays"]) == 3


def test_source_dropout_degrades_supported_to_unknown():
    replay = _replays()["source-dropout-email-confirmation"]
    assert replay["status_transition"] == "Supported->Unknown"
    assert replay["after_preview"]["missing"] == ["email_exam_confirmation"]
    assert replay["summary_delta"]["before_included"] is True
    assert replay["summary_delta"]["preview_included"] is False


def test_missing_evidence_arrival_is_hypothetical_only():
    replay = _replays()["preview-calendar-hackathon-arrival"]
    assert replay["status_transition"] == "Unknown->Supported"
    pointer = next(
        item for item in replay["after_preview"]["pointers"]
        if item["evidence_id"] == "calendar_hackathon_evening"
    )
    assert pointer["hypothetical"] is True
    assert pointer["identity_schema"] == HYPOTHETICAL_IDENTITY_SCHEMA
    assert replay["receipt"]["hypothetical_evidence_promoted_to_observed"] is False


def test_conflict_quarantine_does_not_false_resolve():
    replay = _replays()["quarantine-riverside-conflict-source"]
    assert replay["status_transition"] == "Conflict->Unknown"
    assert replay["after_preview"]["missing"] == ["transaction_location_riverside"]
    assert replay["summary_delta"]["preview_included"] is False
    assert "不能证明" in replay["next_evidence_action"]


def test_canonical_summary_is_immutable_during_every_preview():
    artifact = build_product_v2(PROJECT_ROOT)
    assert artifact["canonical_summary"]["included_case_ids"] == ["DQ-TOP1-POSITIVE-001"]
    assert all(item["summary_delta"]["canonical_baseline_unchanged"] for item in artifact["replays"])
    assert artifact["invariants"]["canonical_summary_immutable_during_preview"] is True


def test_receipts_are_unique_stable_and_bound_to_v1_reports():
    first = build_product_v2(PROJECT_ROOT)
    second = build_product_v2(PROJECT_ROOT)
    first_ids = [item["receipt"]["receipt_id"] for item in first["replays"]]
    second_ids = [item["receipt"]["receipt_id"] for item in second["replays"]]
    assert first_ids == second_ids
    assert len(first_ids) == len(set(first_ids)) == 3
    assert all(item["receipt"]["baseline_mutated"] is False for item in first["replays"])


def test_v2_artifact_is_byte_stable_and_committed():
    artifact = build_product_v2(PROJECT_ROOT)
    assert product_v2_identity(artifact) == product_v2_identity(build_product_v2(PROJECT_ROOT))
    assert OUTPUT.read_text(encoding="utf-8") == canonical_json(artifact)


def test_v2_artifact_is_scoped_and_private_pattern_free():
    artifact = build_product_v2(PROJECT_ROOT)
    text = canonical_json(artifact)
    assert not PRIVATE_OR_PATH.search(text)
    assert "not private-data validation" in artifact["claim_boundary"]
    assert artifact["invariants"]["no_network_or_secret_required"] is True


def test_product_v2_contract_is_parseable_and_ids_resolve():
    contract = json.loads((PROJECT_ROOT / "PRODUCT_V2_CONTRACT.json").read_text("utf-8"))
    ids = [item["intervention_id"] for item in contract["interventions"]]
    assert len(ids) == len(set(ids)) == 3
    assert set(ids) == set(_replays())


def test_mature_comparison_is_fixed_and_explicitly_non_performance():
    rows = build_product_v2(PROJECT_ROOT)["mature_workflow_comparison"]
    assert {item["project"] for item in rows} == {
        "ActivityWatch", "screenpipe", "DailyOS", "Langfuse", "Phoenix"
    }
    assert all(re.fullmatch(r"[0-9a-f]{40}", item["commit"]) for item in rows)
    assert all(
        item["comparison_level"] == "documentation_architecture_workflow_only"
        for item in rows
    )


def test_generated_artifacts_are_pinned_to_lf_checkout_bytes():
    attributes = (PROJECT_ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "artifacts/**/*.json text eol=lf" in attributes
    assert "artifacts/**/*.jsonl text eol=lf" in attributes
