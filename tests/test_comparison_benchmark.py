from pathlib import Path

from dayquest.comparison_benchmark import (
    BENCHMARK_BOUNDARY,
    STRATEGY_ORDER,
    benchmark_identity,
    build_comparison_benchmark,
)
from dayquest.evaluation import canonical_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "artifacts" / "evaluation" / "comparison" / "benchmark.json"


def _strategies(benchmark):
    return {item["strategy_id"]: item for item in benchmark["strategies"]}


def test_benchmark_is_twelve_case_transparent_comparison():
    benchmark = build_comparison_benchmark(PROJECT_ROOT)
    assert benchmark["case_count"] == 12
    assert tuple(item["strategy_id"] for item in benchmark["strategies"]) == STRATEGY_ORDER
    assert all(item["rule"] and item["tradeoff"] for item in benchmark["strategies"])
    assert all(item["kind"] == "transparent_reference_ablation" for item in benchmark["strategies"][1:])


def test_dayquest_closes_frozen_comparison_gates():
    metrics = _strategies(build_comparison_benchmark(PROJECT_ROOT))["dayquest_evidence_gate"]["metrics"]
    assert metrics["status_exact_match"] == {"count": 12, "total": 12, "rate": 1.0}
    assert metrics["false_supported"] == {"count": 0, "total": 9, "rate": 0.0}
    assert metrics["missing_evidence_detection"] == {"count": 7, "total": 7, "rate": 1.0}
    assert metrics["conflict_preservation"] == {"count": 2, "total": 2, "rate": 1.0}
    assert metrics["unsupported_summary_leakage"] == {"count": 0, "total": 12, "rate": 0.0}
    assert metrics["source_pointer_and_gap_coverage"] == {"count": 12, "total": 12, "rate": 1.0}
    assert metrics["safe_tool_failure_handling"] == {"count": 4, "total": 4, "rate": 1.0}


def test_each_ablation_exposes_its_intended_failure_boundary():
    strategies = _strategies(build_comparison_benchmark(PROJECT_ROOT))
    assert strategies["non_unknown_summary"]["metrics"]["unsupported_summary_leakage"]["count"] == 3
    assert strategies["support_wins"]["metrics"]["false_supported"]["count"] == 6
    assert strategies["support_wins"]["metrics"]["conflict_preservation"]["count"] == 0
    assert strategies["optimistic_tool_completion"]["metrics"]["false_supported"]["count"] == 4
    assert strategies["optimistic_tool_completion"]["metrics"]["safe_tool_failure_handling"]["count"] == 0


def test_benchmark_is_byte_stable_and_latency_free():
    first = build_comparison_benchmark(PROJECT_ROOT)
    second = build_comparison_benchmark(PROJECT_ROOT)
    assert benchmark_identity(first) == benchmark_identity(second)
    assert canonical_json(first) == canonical_json(second)
    assert first["determinism"]["local_latency_in_identity"] is False


def test_committed_benchmark_matches_generator_and_scoped_claim():
    benchmark = build_comparison_benchmark(PROJECT_ROOT)
    assert OUTPUT.read_text(encoding="utf-8") == canonical_json(benchmark)
    assert "not mature competitor implementations" in BENCHMARK_BOUNDARY
    assert "not statistical generalization" in BENCHMARK_BOUNDARY
