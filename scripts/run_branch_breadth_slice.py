"""Generate or verify the deterministic Day 3 branch-breadth slice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dayquest.branch_breadth import (  # noqa: E402
    build_branch_breadth_aggregate,
    execute_branch_case,
)
from dayquest.evaluation import canonical_json, sha256_text  # noqa: E402


DAY2_ROOT = PROJECT_ROOT / "artifacts" / "evaluation" / "day2"
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "evaluation" / "day3"
CONTRACT_ROOT = ARTIFACT_ROOT / "contracts"
REPORT_ROOT = ARTIFACT_ROOT / "reports"
AGGREGATE_OUTPUT = ARTIFACT_ROOT / "aggregate.json"


def _load_new_contracts() -> list[dict[str, object]]:
    contracts = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CONTRACT_ROOT.glob("*.json"))
    ]
    if [contract["case_id"] for contract in contracts] != [
        "DQ-EVAL-MAX-ITERATION-001",
        "DQ-EVAL-NEXLA-RECOVERY-001",
        "DQ-EVAL-POLICY-COUNTEREXAMPLE-001",
    ]:
        raise RuntimeError("unexpected_day3_case_set")
    return contracts


def _load_day2_reports() -> list[dict[str, object]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((DAY2_ROOT / "reports").glob("*.json"))
    ]


def build_outputs() -> dict[Path, str]:
    new_reports = [
        execute_branch_case(contract, PROJECT_ROOT) for contract in _load_new_contracts()
    ]
    all_reports = sorted(
        [*_load_day2_reports(), *new_reports], key=lambda report: report["case_id"]
    )
    outputs = {
        REPORT_ROOT / f"{report['case_id']}.json": canonical_json(report)
        for report in new_reports
    }
    outputs[AGGREGATE_OUTPUT] = canonical_json(
        build_branch_breadth_aggregate(all_reports)
    )
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    outputs = build_outputs()
    mismatches: list[str] = []
    for path, content in outputs.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                mismatches.append(path.relative_to(PROJECT_ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")

    if mismatches:
        print(f"artifact_mismatch={','.join(mismatches)}")
        return 1

    aggregate = json.loads(outputs[AGGREGATE_OUTPUT])
    counts = aggregate["counts"]
    print(f"slice={aggregate['slice_label']}")
    print(f"cases={counts['total']}")
    print(
        "judgments="
        f"supported:{counts['supported']},"
        f"failed:{counts['failed']},"
        f"unknown:{counts['unknown']}"
    )
    print(
        "branch_metrics="
        f"recovery_success:{counts['recovery_success']},"
        f"unsafe_continuation:{counts['unsafe_continuation']},"
        f"policy_violations:{counts['policy_violations']}"
    )
    print(f"aggregate_sha256={sha256_text(outputs[AGGREGATE_OUTPUT])}")
    print(f"path={AGGREGATE_OUTPUT.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
