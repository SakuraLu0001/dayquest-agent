"""Deterministic Product V2 evidence replay over immutable V1 reports."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .evaluation import CANONICAL_JSON_HASH_BASIS, canonical_json, sha256_text
from .product_timeline import DISPLAY_COPY, PRODUCT_CASE_IDS, build_product_demo


PRODUCT_V2_SCHEMA_VERSION = "dayquest.product_v2_replay.v1"
PRODUCT_V2_ARTIFACT_ID = "DQ-PRODUCT-V2-EPISTEMIC-REPLAY-001"
HYPOTHETICAL_IDENTITY_SCHEMA = "dayquest.hypothetical_evidence_identity.v1"
INTERVENTION_RECEIPT_SCHEMA = "dayquest.intervention_receipt.v1"
CONTRACT_PATHS = {
    "DQ-TOP1-POSITIVE-001": "artifacts/evaluation/top1/vs1/contracts/DQ-TOP1-POSITIVE-001.json",
    "DQ-TOP1-MISSING-002": "artifacts/evaluation/top1/mvp/contracts/DQ-TOP1-MISSING-002.json",
    "DQ-TOP1-CONFLICT-002": "artifacts/evaluation/top1/mvp/contracts/DQ-TOP1-CONFLICT-002.json",
}
INTERVENTION_COPY = {
    "source-dropout-email-confirmation": {
        "label": "模拟邮件来源丢失",
        "description": "暂时移除已观察到的邮件确认，检查一个原本 Supported 的事实是否安全降级。",
    },
    "preview-calendar-hackathon-arrival": {
        "label": "预览缺失日历证据到达",
        "description": "加入明确标记为 hypothetical 的日历证据，预览 Unknown 是否可转为 Supported；不写回事实基线。",
    },
    "quarantine-riverside-conflict-source": {
        "label": "隔离冲突来源",
        "description": "隔离与 Guild Hall 冲突的 Riverside 记录；检查系统是否保守变为 Unknown，而不是把剩余支持自动当真。",
    },
}
MATURE_WORKFLOW_COMPARISON = [
    {
        "project": "ActivityWatch",
        "commit": "5d26465fd54e513e9e912bb410e08ac52facfb4d",
        "mature_workflow": "local activity collection, timeline/query, raw-event inspection, export",
        "dayquest_v2_gap": "replay claim-state changes from bounded evidence interventions with immutable receipts",
        "comparison_level": "documentation_architecture_workflow_only",
    },
    {
        "project": "screenpipe",
        "commit": "dd071b490d4dc5067e67b104723cc4992094c377",
        "mature_workflow": "local screen/audio capture, search, timeline, local API and automation",
        "dayquest_v2_gap": "show why a personal-activity claim changes between Supported, Unknown and Conflict",
        "comparison_level": "documentation_architecture_workflow_only",
    },
    {
        "project": "DailyOS",
        "commit": "34a06910b87a897cfd00447df71b0788fad960b3",
        "mature_workflow": "local multi-source daily planning with source-linked briefs and partial-failure visibility",
        "dayquest_v2_gap": "preview evidence removal, arrival and quarantine without rewriting the canonical day",
        "comparison_level": "documentation_architecture_workflow_only",
    },
    {
        "project": "Langfuse",
        "commit": "1124345b79bbf1ffe346abc8cbd4c35bb51a2ac1",
        "mature_workflow": "tracing, datasets, evaluation and experiment comparison",
        "dayquest_v2_gap": "a domain-specific epistemic replay receipt bound to personal-activity evidence",
        "comparison_level": "documentation_architecture_workflow_only",
    },
    {
        "project": "Phoenix",
        "commit": "37916d7351002222fc5a3ee8560528834da85134",
        "mature_workflow": "OpenTelemetry/OpenInference traces, evaluations, datasets and experiment replay",
        "dayquest_v2_gap": "conservative summary propagation when evidence sufficiency changes",
        "comparison_level": "documentation_architecture_workflow_only",
    },
]


def _load_json(project_root: Path, relative: str) -> dict[str, Any]:
    return json.loads((project_root / relative).read_text(encoding="utf-8"))


def _report(project_root: Path, case_id: str) -> dict[str, Any]:
    return _load_json(
        project_root,
        f"artifacts/evaluation/top1/mvp/reports/{case_id}.json",
    )


def _requirement_map(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["evidence_id"]: item for item in contract["required_evidence"]}


def _baseline_pointers(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pointers = [
        *report["evidence_review"]["supporting_pointers"],
        *report["evidence_review"]["contradicting_pointers"],
    ]
    return {
        pointer["evidence_id"]: {**copy.deepcopy(pointer), "hypothetical": False}
        for pointer in pointers
    }


def _hypothetical_pointer(requirement: dict[str, Any]) -> dict[str, Any]:
    material = {
        "schema_version": HYPOTHETICAL_IDENTITY_SCHEMA,
        "evidence_id": requirement["evidence_id"],
        "match": requirement["match"],
        "evidence_role": requirement.get("evidence_role", "supporting"),
    }
    return {
        "source": requirement["match"]["source"],
        "safe_record_id": f"hyp-v1-{sha256_text(canonical_json(material))}",
        "identity_schema": HYPOTHETICAL_IDENTITY_SCHEMA,
        "field": requirement["pointer_field"],
        "evidence_role": requirement.get("evidence_role", "supporting"),
        "evidence_id": requirement["evidence_id"],
        "hypothetical": True,
    }


def _status(
    pointers: dict[str, dict[str, Any]],
    missing: list[str],
) -> str:
    supporting = [item for item in pointers.values() if item["evidence_role"] == "supporting"]
    contradicting = [item for item in pointers.values() if item["evidence_role"] == "contradicting"]
    if supporting and contradicting:
        return "Conflict"
    if missing:
        return "Unknown"
    return "Supported"


def _next_evidence_action(
    intervention_id: str,
    evidence_id: str,
) -> str:
    if intervention_id == "source-dropout-email-confirmation":
        return f"恢复或重新取得 observed evidence `{evidence_id}`；在此之前保持 Unknown。"
    if intervention_id == "preview-calendar-hackathon-arrival":
        return f"从真实只读来源验证 `{evidence_id}` 后才能从 preview 晋升为 observed evidence。"
    return (
        "隔离冲突记录只会减少可用证据，不能证明剩余来源正确；"
        "需要独立的 adjudicating evidence（裁定证据）后才能解决 Conflict。"
    )


def _build_receipt(
    *,
    contract_id: str,
    report: dict[str, Any],
    intervention: dict[str, Any],
    before_status: str,
    after_status: str,
    before_missing: list[str],
    after_missing: list[str],
    changed_pointer: dict[str, Any] | None,
) -> dict[str, Any]:
    receipt = {
        "schema_version": INTERVENTION_RECEIPT_SCHEMA,
        "product_contract_id": contract_id,
        "case_id": report["case_id"],
        "baseline_report_sha256": sha256_text(canonical_json(report)),
        "baseline_report_hash_basis": CANONICAL_JSON_HASH_BASIS,
        "intervention_id": intervention["intervention_id"],
        "operation": intervention["operation"],
        "evidence_id": intervention["evidence_id"],
        "before_status": before_status,
        "after_status": after_status,
        "before_missing": before_missing,
        "after_missing": after_missing,
        "changed_pointer": changed_pointer,
        "baseline_mutated": False,
        "preview_only": True,
        "hypothetical_evidence_promoted_to_observed": False,
    }
    return {
        **receipt,
        "receipt_id": f"v2-receipt-{sha256_text(canonical_json(receipt))}",
        "receipt_hash_basis": CANONICAL_JSON_HASH_BASIS,
    }


def replay_intervention(
    project_root: Path,
    product_contract: dict[str, Any],
    intervention: dict[str, Any],
) -> dict[str, Any]:
    case_id = intervention["case_id"]
    report = _report(project_root, case_id)
    claim = report["timeline"][0]
    claim_contract = _load_json(project_root, CONTRACT_PATHS[case_id])
    requirements = _requirement_map(claim_contract)
    evidence_id = intervention["evidence_id"]
    if evidence_id not in requirements:
        raise ValueError(f"intervention_evidence_not_required:{evidence_id}")

    before_pointers = _baseline_pointers(report)
    before_missing = sorted(report["evidence_review"]["missing_requirements"])
    before_status = _status(before_pointers, before_missing)
    if before_status != claim["status"]:
        raise ValueError(f"baseline_replay_status_mismatch:{case_id}")

    after_pointers = copy.deepcopy(before_pointers)
    after_missing = list(before_missing)
    changed_pointer: dict[str, Any] | None = None
    if intervention["operation"] == "add_hypothetical_evidence":
        if evidence_id not in after_missing:
            raise ValueError(f"hypothetical_target_not_missing:{evidence_id}")
        changed_pointer = _hypothetical_pointer(requirements[evidence_id])
        after_pointers[evidence_id] = changed_pointer
        after_missing.remove(evidence_id)
    elif intervention["operation"] in {
        "remove_observed_evidence",
        "quarantine_observed_evidence",
    }:
        changed_pointer = after_pointers.pop(evidence_id, None)
        if not changed_pointer or changed_pointer["hypothetical"]:
            raise ValueError(f"observed_intervention_target_invalid:{evidence_id}")
        after_missing.append(evidence_id)
    else:
        raise ValueError(f"unsupported_intervention_operation:{intervention['operation']}")

    after_missing = sorted(set(after_missing))
    after_status = _status(after_pointers, after_missing)
    observed_transition = f"{before_status}->{after_status}"
    if observed_transition != intervention["expected_transition"]:
        raise ValueError(
            f"unexpected_intervention_transition:{intervention['intervention_id']}:{observed_transition}"
        )

    policy_compliant = report["policy"]["observed"] == "compliant"
    before_summary_eligible = before_status == "Supported" and policy_compliant
    preview_summary_eligible = after_status == "Supported" and policy_compliant
    receipt = _build_receipt(
        contract_id=product_contract["contract_id"],
        report=report,
        intervention=intervention,
        before_status=before_status,
        after_status=after_status,
        before_missing=before_missing,
        after_missing=after_missing,
        changed_pointer=changed_pointer,
    )
    return {
        "intervention_id": intervention["intervention_id"],
        "label": INTERVENTION_COPY[intervention["intervention_id"]]["label"],
        "description": INTERVENTION_COPY[intervention["intervention_id"]]["description"],
        "case_id": case_id,
        "title": DISPLAY_COPY[case_id]["title"],
        "statement": claim["statement"],
        "operation": intervention["operation"],
        "evidence_id": evidence_id,
        "before": {
            "status": before_status,
            "pointers": [before_pointers[key] for key in sorted(before_pointers)],
            "missing": before_missing,
            "summary_eligible": before_summary_eligible,
        },
        "after_preview": {
            "status": after_status,
            "pointers": [after_pointers[key] for key in sorted(after_pointers)],
            "missing": after_missing,
            "summary_eligible": preview_summary_eligible,
            "contains_hypothetical_evidence": any(
                pointer["hypothetical"] for pointer in after_pointers.values()
            ),
        },
        "status_transition": observed_transition,
        "summary_delta": {
            "canonical_baseline_unchanged": True,
            "before_included": before_summary_eligible,
            "preview_included": preview_summary_eligible,
            "preview_fact": (
                DISPLAY_COPY[case_id]["summary_fact"] if preview_summary_eligible else None
            ),
        },
        "next_evidence_action": _next_evidence_action(
            intervention["intervention_id"], evidence_id
        ),
        "receipt": receipt,
    }


def _source_health(
    project_root: Path,
    reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, int]] = {}
    for report in reports:
        contract = _load_json(project_root, CONTRACT_PATHS[report["case_id"]])
        requirements = _requirement_map(contract)
        observed_ids = set(_baseline_pointers(report))
        missing_ids = set(report["evidence_review"]["missing_requirements"])
        for evidence_id, requirement in requirements.items():
            source = requirement["match"]["source"]
            source_counts = counts.setdefault(
                source,
                {"required": 0, "observed": 0, "missing": 0, "contradicting": 0},
            )
            source_counts["required"] += 1
            source_counts["observed"] += evidence_id in observed_ids
            source_counts["missing"] += evidence_id in missing_ids
            source_counts["contradicting"] += (
                evidence_id in observed_ids
                and requirement.get("evidence_role", "supporting") == "contradicting"
            )
    return [
        {
            "source": source,
            **counts[source],
            "health": (
                "conflict_present"
                if counts[source]["contradicting"]
                else "incomplete"
                if counts[source]["missing"]
                else "observed"
            ),
        }
        for source in sorted(counts)
    ]


def build_product_v2(project_root: Path) -> dict[str, Any]:
    product_contract = _load_json(project_root, "PRODUCT_V2_CONTRACT.json")
    if product_contract["contract_id"] != PRODUCT_V2_ARTIFACT_ID:
        raise ValueError("product_v2_contract_identity_mismatch")
    baseline = build_product_demo(project_root)
    reports = [_report(project_root, case_id) for case_id in PRODUCT_CASE_IDS]
    replays = [
        replay_intervention(project_root, product_contract, intervention)
        for intervention in product_contract["interventions"]
    ]
    return {
        "schema_version": PRODUCT_V2_SCHEMA_VERSION,
        "artifact_id": PRODUCT_V2_ARTIFACT_ID,
        "product_positioning": product_contract["top_1_positioning"],
        "baseline_demo_id": baseline["demo_id"],
        "baseline_report_sha256": {
            report["case_id"]: sha256_text(canonical_json(report)) for report in reports
        },
        "baseline_timeline": baseline["timeline"],
        "canonical_summary": baseline["constrained_summary"],
        "source_health": _source_health(project_root, reports),
        "mature_workflow_comparison": MATURE_WORKFLOW_COMPARISON,
        "replays": replays,
        "transition_counts": {
            transition: sum(item["status_transition"] == transition for item in replays)
            for transition in (
                "Supported->Unknown",
                "Unknown->Supported",
                "Conflict->Unknown",
            )
        },
        "invariants": product_contract["invariants"],
        "artifact_hash_basis": CANONICAL_JSON_HASH_BASIS,
        "claim_boundary": product_contract["claim_boundary"],
    }


def product_v2_identity(artifact: dict[str, Any]) -> str:
    return sha256_text(canonical_json(artifact))
