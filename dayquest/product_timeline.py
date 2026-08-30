"""User-facing synthetic-safe day model built from accepted MVP evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PRODUCT_DEMO_SCHEMA_VERSION = "dayquest.product_timeline_demo.v1"
PRODUCT_DEMO_ID = "dayquest-synthetic-safe-my-day-v1"
PRODUCT_CASE_IDS = (
    "DQ-TOP1-POSITIVE-001",
    "DQ-TOP1-MISSING-002",
    "DQ-TOP1-CONFLICT-002",
)
TIME_ORDER = {"morning": 0, "afternoon": 1, "evening": 2, "unknown": 3}
DISPLAY_COPY = {
    "DQ-TOP1-POSITIVE-001": {"title": "语言认证考试", "summary_fact": "上午完成了语言认证考试。"},
    "DQ-TOP1-MISSING-002": {"title": "晚间黑客松", "summary_fact": "晚上参加了黑客松。"},
    "DQ-TOP1-CONFLICT-002": {"title": "黑客松地点", "summary_fact": "黑客松在 Guild Hall 举行。"},
}
STATUS_LABELS = {"Supported": "已支持", "Unknown": "证据不足", "Conflict": "证据冲突"}


def _load_report(project_root: Path, case_id: str) -> dict[str, Any]:
    path = project_root / "artifacts" / "evaluation" / "top1" / "mvp" / "reports" / f"{case_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _timeline_item(report: dict[str, Any]) -> dict[str, Any]:
    claim = report["timeline"][0]
    case_id = report["case_id"]
    status = claim["status"]
    policy_compliant = report["policy"]["observed"] == "compliant"
    summary_eligible = status == "Supported" and policy_compliant
    return {
        "case_id": case_id,
        "title": DISPLAY_COPY[case_id]["title"],
        "statement": claim["statement"],
        "time_range": claim["time_range"],
        "status": status,
        "status_label": STATUS_LABELS[status],
        "decision_reason": claim["decision_reason"],
        "supporting_pointers": report["evidence_review"]["supporting_pointers"],
        "contradicting_pointers": report["evidence_review"]["contradicting_pointers"],
        "missing_requirements": report["evidence_review"]["missing_requirements"],
        "policy_status": report["policy"]["observed"],
        "policy_violations": report["policy"]["violations"],
        "summary_eligible": summary_eligible,
        "summary_fact": DISPLAY_COPY[case_id]["summary_fact"] if summary_eligible else None,
        "evidence_lineage": report["evidence_lineage"],
    }


def build_product_demo(project_root: Path) -> dict[str, Any]:
    """Build one readable day without promoting Unknown or Conflict to fact."""
    items = [_timeline_item(_load_report(project_root, case_id)) for case_id in PRODUCT_CASE_IDS]
    product_order = {case_id: index for index, case_id in enumerate(PRODUCT_CASE_IDS)}
    items.sort(key=lambda item: (TIME_ORDER.get(item["time_range"], 99), product_order[item["case_id"]]))
    if {item["status"] for item in items} != {"Supported", "Unknown", "Conflict"}:
        raise ValueError("product_demo_status_coverage_invalid")
    included = [item for item in items if item["summary_eligible"]]
    excluded = [item for item in items if not item["summary_eligible"]]
    summary = " ".join(item["summary_fact"] for item in included)
    return {
        "schema_version": PRODUCT_DEMO_SCHEMA_VERSION,
        "demo_id": PRODUCT_DEMO_ID,
        "fixture_label": "Synthetic-safe Day · 本地演示",
        "date_label": "示例日",
        "timeline": items,
        "constrained_summary": {
            "text": summary or "当前没有足够证据形成事实摘要。",
            "included_case_ids": [item["case_id"] for item in included],
            "excluded": [
                {"case_id": item["case_id"], "status": item["status"], "reason": "claim_not_supported_or_policy_not_compliant"}
                for item in excluded
            ],
            "rule": "Only Supported and policy-compliant claims may become facts.",
        },
        "counts": {
            "items": len(items),
            "supported": sum(item["status"] == "Supported" for item in items),
            "unknown": sum(item["status"] == "Unknown" for item in items),
            "conflict": sum(item["status"] == "Conflict" for item in items),
            "summary_facts": len(included),
        },
        "boundary": "Synthetic-safe local product demonstration built from committed MVP reports; not private-data validation or a production reliability claim.",
    }
