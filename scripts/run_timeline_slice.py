"""Generate or verify the two-case Top-1 timeline vertical slice."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dayquest.evaluation import canonical_json, sha256_text  # noqa: E402
from dayquest.mcp_timeline_client import (  # noqa: E402
    fetch_timeline_inputs,
    running_local_mcp_server,
)
from dayquest.timeline_evaluation import (  # noqa: E402
    build_timeline_aggregate,
    execute_timeline_case,
)


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "evaluation" / "top1" / "vs1"
CONTRACT_ROOT = ARTIFACT_ROOT / "contracts"
REPORT_ROOT = ARTIFACT_ROOT / "reports"
AGGREGATE_OUTPUT = ARTIFACT_ROOT / "aggregate.json"
EXPECTED_CASE_IDS = ["DQ-TOP1-MISSING-001", "DQ-TOP1-POSITIVE-001"]


def _load_contracts() -> list[dict[str, object]]:
    contracts = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CONTRACT_ROOT.glob("*.json"))
    ]
    if [contract["case_id"] for contract in contracts] != EXPECTED_CASE_IDS:
        raise RuntimeError("unexpected_top1_vs1_case_set")
    return contracts


def build_outputs() -> dict[Path, str]:
    reports: list[dict[str, object]] = []
    with running_local_mcp_server(PROJECT_ROOT):
        for contract in _load_contracts():
            transport_result = asyncio.run(
                fetch_timeline_inputs(int(contract["tool_limit"]))
            )
            reports.append(execute_timeline_case(contract, transport_result))
    reports.sort(key=lambda report: report["case_id"])
    outputs = {
        REPORT_ROOT / f"{report['case_id']}.json": canonical_json(report)
        for report in reports
    }
    outputs[AGGREGATE_OUTPUT] = canonical_json(build_timeline_aggregate(reports))
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        outputs = build_outputs()
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"vs1_status=failed reason={exc}", file=sys.stderr)
        return 1

    mismatches: list[str] = []
    for path, content in outputs.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                mismatches.append(path.relative_to(PROJECT_ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    if mismatches:
        print(f"vs1_status=failed artifact_mismatch={','.join(mismatches)}")
        return 1

    aggregate = json.loads(outputs[AGGREGATE_OUTPUT])
    print("vs1_status=verified")
    for case_id in EXPECTED_CASE_IDS:
        report = json.loads(outputs[REPORT_ROOT / f"{case_id}.json"])
        claim = report["timeline"][0]
        print(
            f"case={case_id} status={claim['status']} "
            f"source_pointers={len(claim['source_pointers'])} "
            f"missing_required={len(claim['missing_required_evidence'])}"
        )
        print(f"timeline={claim['statement']}")
    counts = aggregate["counts"]
    print(
        "evidence_gate="
        f"real_mcp:{counts['real_mcp_transport']}/2,"
        f"status_match:{counts['status_exact_match']}/2,"
        f"source_pointer:{counts['source_pointer_complete']}/1,"
        f"missing_requirement:{counts['missing_requirement_complete']}/1,"
        f"false_supported:{counts['false_supported']},"
        f"privacy_leaks:{counts['privacy_or_absolute_path_leaks']}"
    )
    print(f"aggregate_sha256={sha256_text(outputs[AGGREGATE_OUTPUT])}")
    print(f"aggregate_path={AGGREGATE_OUTPUT.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
