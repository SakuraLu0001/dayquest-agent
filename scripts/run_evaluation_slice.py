"""Generate or verify the deterministic DayQuest Day 2 evaluation slice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dayquest.evaluation import build_aggregate, canonical_json, execute_case, sha256_text  # noqa: E402


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "evaluation" / "day2"
CONTRACT_ROOT = ARTIFACT_ROOT / "contracts"
REPORT_ROOT = ARTIFACT_ROOT / "reports"
AGGREGATE_OUTPUT = ARTIFACT_ROOT / "aggregate.json"


def _load_contracts() -> list[dict[str, object]]:
    contracts = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(CONTRACT_ROOT.glob("*.json"))]
    if [contract["case_id"] for contract in contracts] != [
        "DQ-EVAL-BASELINE-001",
        "DQ-EVAL-LOCAL-ERROR-001",
    ]:
        raise RuntimeError("unexpected_day2_case_set")
    return contracts


def build_outputs() -> dict[Path, str]:
    reports = [execute_case(contract, PROJECT_ROOT) for contract in _load_contracts()]
    outputs = {REPORT_ROOT / f"{report['case_id']}.json": canonical_json(report) for report in reports}
    outputs[AGGREGATE_OUTPUT] = canonical_json(build_aggregate(reports))
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
    print("slice=Day 2 development slice")
    print(f"cases={aggregate['counts']['total']}")
    print(
        "judgments="
        f"supported:{aggregate['counts']['supported']},"
        f"failed:{aggregate['counts']['failed']},"
        f"unknown:{aggregate['counts']['unknown']}"
    )
    print(f"aggregate_sha256={sha256_text(outputs[AGGREGATE_OUTPUT])}")
    print(f"path={AGGREGATE_OUTPUT.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
