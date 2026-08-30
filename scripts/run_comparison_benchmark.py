"""Generate or verify the transparent twelve-case comparison benchmark."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dayquest.comparison_benchmark import benchmark_identity, build_comparison_benchmark  # noqa: E402
from dayquest.evaluation import canonical_json  # noqa: E402


OUTPUT = PROJECT_ROOT / "artifacts" / "evaluation" / "comparison" / "benchmark.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    first = build_comparison_benchmark(PROJECT_ROOT)
    second = build_comparison_benchmark(PROJECT_ROOT)
    first_text = canonical_json(first)
    second_text = canonical_json(second)
    if first_text != second_text:
        print("comparison_status=failed reason=two_build_identity_mismatch", file=sys.stderr)
        return 1
    if args.generate:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(first_text, encoding="utf-8", newline="\n")
    elif not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != first_text:
        print("comparison_status=failed reason=committed_artifact_mismatch", file=sys.stderr)
        return 1
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    dayquest = first["strategies"][0]["metrics"]
    print(
        "comparison_status=verified "
        f"cases={first['case_count']} strategies={len(first['strategies'])} "
        f"false_supported={dayquest['false_supported']['count']} "
        f"conflicts_preserved={dayquest['conflict_preservation']['count']} "
        f"unsupported_summary_leaks={dayquest['unsupported_summary_leakage']['count']}"
    )
    print(f"benchmark_sha256={benchmark_identity(first)}")
    print(f"local_two_build_elapsed_ms={elapsed_ms} basis=observed_not_artifact_identity")
    print(f"benchmark_path={OUTPUT.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
