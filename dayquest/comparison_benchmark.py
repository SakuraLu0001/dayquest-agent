"""Transparent deterministic baselines for the committed DayQuest MVP reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from .evaluation import CANONICAL_JSON_HASH_BASIS, canonical_json, sha256_text
from .timeline_mvp import EXPECTED_CASE_IDS, TOOL_FAILURE_CASE_IDS


BENCHMARK_SCHEMA_VERSION = "dayquest.comparison_benchmark.v1"
BENCHMARK_ID = "DQ-COMPARE-12CASE-001"
BENCHMARK_BOUNDARY = (
    "Deterministic comparison on twelve committed synthetic-safe development cases. "
    "Reference strategies are intentionally simple transparent ablations, not mature "
    "competitor implementations; results are not statistical generalization, production "
    "reliability, private-data applicability, or a universal superiority claim."
)
STRATEGY_ORDER = (
    "dayquest_evidence_gate",
    "non_unknown_summary",
    "support_wins",
    "optimistic_tool_completion",
)
STRATEGY_DESCRIPTIONS = {
    "dayquest_evidence_gate": {
        "kind": "implemented_system",
        "rule": "Preserve Supported/Unknown/Conflict, require policy compliance for summary, and retain evidence gaps and pointers.",
        "tradeoff": "Conservative: a useful fact may remain Unknown until required evidence arrives.",
    },
    "non_unknown_summary": {
        "kind": "transparent_reference_ablation",
        "rule": "Keep the checker status but summarize every non-Unknown claim and ignore policy at the summary gate.",
        "tradeoff": "More complete-looking summaries can factualize Conflict or policy-violating claims.",
    },
    "support_wins": {
        "kind": "transparent_reference_ablation",
        "rule": "Any supporting pointer makes a claim Supported; contradictory pointers and remaining requirements are dropped.",
        "tradeoff": "Simple and optimistic, but partial or contradicted evidence can false-pass.",
    },
    "optimistic_tool_completion": {
        "kind": "transparent_reference_ablation",
        "rule": "Keep normal-case decisions but promote every tool-failure case to Supported and summary-eligible.",
        "tradeoff": "Avoids empty outputs after faults, but converts missing acquisition evidence into facts.",
    },
}


def load_committed_reports(project_root: Path) -> list[dict[str, Any]]:
    report_root = project_root / "artifacts" / "evaluation" / "top1" / "mvp" / "reports"
    reports = [
        json.loads((report_root / f"{case_id}.json").read_text(encoding="utf-8"))
        for case_id in EXPECTED_CASE_IDS
    ]
    if [report["case_id"] for report in reports] != EXPECTED_CASE_IDS:
        raise ValueError("comparison_source_case_set_invalid")
    return reports


def _reference(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": report["case_id"],
        "expected_status": report["evaluation"]["expected_claim_status"],
        "policy": report["policy"]["observed"],
        "supporting": report["evidence_review"]["supporting_pointers"],
        "contradicting": report["evidence_review"]["contradicting_pointers"],
        "missing": report["evidence_review"]["missing_requirements"],
        "tool_failure": report["case_id"] in TOOL_FAILURE_CASE_IDS,
        "correct_tool_safe_behavior": report["tool_behavior"]["correct_safe_behavior"],
    }


def _dayquest(reference: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    status = report["timeline"][0]["status"]
    return {
        "status": status,
        "summary_emitted": status == "Supported" and reference["policy"] == "compliant",
        "supporting": reference["supporting"],
        "contradicting": reference["contradicting"],
        "missing": reference["missing"],
        "safe_tool_failure": bool(reference["correct_tool_safe_behavior"]),
    }


def _non_unknown_summary(reference: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    result = _dayquest(reference, report)
    result["summary_emitted"] = result["status"] != "Unknown"
    return result


def _support_wins(reference: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    del report
    status = "Supported" if reference["supporting"] else "Unknown"
    return {
        "status": status,
        "summary_emitted": status == "Supported",
        "supporting": reference["supporting"],
        "contradicting": [],
        "missing": [] if status == "Supported" else reference["missing"],
        "safe_tool_failure": reference["tool_failure"] and status == "Unknown",
    }


def _optimistic_tool_completion(reference: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    result = _dayquest(reference, report)
    if reference["tool_failure"]:
        result.update(
            status="Supported",
            summary_emitted=True,
            missing=[],
            safe_tool_failure=False,
        )
    return result


STRATEGIES: dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = {
    "dayquest_evidence_gate": _dayquest,
    "non_unknown_summary": _non_unknown_summary,
    "support_wins": _support_wins,
    "optimistic_tool_completion": _optimistic_tool_completion,
}


def _ratio(count: int, total: int) -> dict[str, int | float]:
    return {"count": count, "total": total, "rate": round(count / total, 6) if total else 0.0}


def _evaluate_strategy(name: str, reports: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for report in reports:
        reference = _reference(report)
        observed = STRATEGIES[name](reference, report)
        all_pointers_retained = (
            observed["supporting"] == reference["supporting"]
            and observed["contradicting"] == reference["contradicting"]
            and observed["missing"] == reference["missing"]
        )
        unsupported_summary = observed["summary_emitted"] and (
            reference["expected_status"] != "Supported" or reference["policy"] != "compliant"
        )
        rows.append(
            {
                "case_id": reference["case_id"],
                "expected_status": reference["expected_status"],
                "observed_status": observed["status"],
                "policy": reference["policy"],
                "summary_emitted": observed["summary_emitted"],
                "unsupported_summary": unsupported_summary,
                "all_reference_evidence_retained": all_pointers_retained,
                "safe_tool_failure": observed["safe_tool_failure"],
            }
        )
    unknown_rows = [row for row in rows if row["expected_status"] == "Unknown"]
    conflict_rows = [row for row in rows if row["expected_status"] == "Conflict"]
    tool_rows = [row for row in rows if row["case_id"] in TOOL_FAILURE_CASE_IDS]
    false_supported = sum(
        row["observed_status"] == "Supported" and row["expected_status"] != "Supported"
        for row in rows
    )
    metrics = {
        "status_exact_match": _ratio(sum(row["observed_status"] == row["expected_status"] for row in rows), len(rows)),
        "false_supported": _ratio(false_supported, sum(row["expected_status"] != "Supported" for row in rows)),
        "missing_evidence_detection": _ratio(sum(row["observed_status"] == "Unknown" for row in unknown_rows), len(unknown_rows)),
        "conflict_preservation": _ratio(sum(row["observed_status"] == "Conflict" for row in conflict_rows), len(conflict_rows)),
        "unsupported_summary_leakage": _ratio(sum(row["unsupported_summary"] for row in rows), len(rows)),
        "source_pointer_and_gap_coverage": _ratio(sum(row["all_reference_evidence_retained"] for row in rows), len(rows)),
        "safe_tool_failure_handling": _ratio(sum(row["safe_tool_failure"] for row in tool_rows), len(tool_rows)),
    }
    return {
        "strategy_id": name,
        **STRATEGY_DESCRIPTIONS[name],
        "metrics": metrics,
        "cases": rows,
    }


def build_comparison_benchmark(project_root: Path) -> dict[str, Any]:
    reports = load_committed_reports(project_root)
    source_aggregate = project_root / "artifacts" / "evaluation" / "top1" / "mvp" / "aggregate.json"
    strategies = [_evaluate_strategy(name, reports) for name in STRATEGY_ORDER]
    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "case_ids": EXPECTED_CASE_IDS,
        "case_count": len(reports),
        "source": {
            "artifact": "artifacts/evaluation/top1/mvp/aggregate.json",
            "raw_file_sha256": hashlib.sha256(source_aggregate.read_bytes()).hexdigest().upper(),
            "report_inputs": "twelve committed dayquest.timeline_mvp_report.v2 files",
        },
        "strategies": strategies,
        "determinism": {
            "artifact_identity_basis": CANONICAL_JSON_HASH_BASIS,
            "local_latency_in_identity": False,
            "two_build_check_required": True,
        },
        "benchmark_boundary": BENCHMARK_BOUNDARY,
    }


def benchmark_identity(benchmark: dict[str, Any]) -> str:
    return sha256_text(canonical_json(benchmark))
