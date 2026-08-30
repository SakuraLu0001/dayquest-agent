from pathlib import Path

from dayquest.product_timeline import PRODUCT_CASE_IDS, PRODUCT_DEMO_ID, build_product_demo


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_product_demo_is_one_complete_three_state_day():
    demo = build_product_demo(PROJECT_ROOT)
    assert demo["demo_id"] == PRODUCT_DEMO_ID
    assert [item["case_id"] for item in demo["timeline"]] == list(PRODUCT_CASE_IDS)
    assert demo["counts"] == {"items": 3, "supported": 1, "unknown": 1, "conflict": 1, "summary_facts": 1}


def test_product_timeline_is_time_sorted():
    demo = build_product_demo(PROJECT_ROOT)
    ranks = {"morning": 0, "afternoon": 1, "evening": 2, "unknown": 3}
    observed = [ranks[item["time_range"]] for item in demo["timeline"]]
    assert observed == sorted(observed)


def test_summary_only_uses_supported_policy_compliant_claims():
    summary = build_product_demo(PROJECT_ROOT)["constrained_summary"]
    assert summary["included_case_ids"] == ["DQ-TOP1-POSITIVE-001"]
    assert {item["case_id"] for item in summary["excluded"]} == {"DQ-TOP1-MISSING-002", "DQ-TOP1-CONFLICT-002"}
    assert "黑客松" not in summary["text"]


def test_unknown_names_missing_requirement():
    unknown = next(item for item in build_product_demo(PROJECT_ROOT)["timeline"] if item["status"] == "Unknown")
    assert unknown["missing_requirements"] == ["calendar_hackathon_evening"]
    assert unknown["summary_eligible"] is False


def test_conflict_keeps_both_evidence_sides():
    conflict = next(item for item in build_product_demo(PROJECT_ROOT)["timeline"] if item["status"] == "Conflict")
    assert conflict["supporting_pointers"]
    assert conflict["contradicting_pointers"]
    assert conflict["summary_eligible"] is False


def test_product_demo_uses_existing_lineage_and_scoped_boundary():
    demo = build_product_demo(PROJECT_ROOT)
    assert all("evidence_lineage" in item for item in demo["timeline"])
    assert "not private-data validation" in demo["boundary"]
