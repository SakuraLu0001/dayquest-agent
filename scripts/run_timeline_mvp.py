"""Generate, verify, or review the twelve-case evidence timeline MVP."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dayquest.evaluation import canonical_json, sha256_text  # noqa: E402
from dayquest.timeline_mvp import (  # noqa: E402
    EXPECTED_CASE_IDS,
    build_mvp_aggregate,
    build_mvp_reports,
)


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "evaluation" / "top1" / "mvp"
REPORT_ROOT = ARTIFACT_ROOT / "reports"
AGGREGATE_OUTPUT = ARTIFACT_ROOT / "aggregate.json"


def build_outputs() -> dict[Path, str]:
    reports = build_mvp_reports(PROJECT_ROOT)
    outputs = {
        REPORT_ROOT / f"{report['case_id']}.json": canonical_json(report)
        for report in reports
    }
    outputs[AGGREGATE_OUTPUT] = canonical_json(
        build_mvp_aggregate(reports, PROJECT_ROOT)
    )
    return outputs


def _write_or_check(outputs: dict[Path, str], *, check: bool) -> list[str]:
    mismatches: list[str] = []
    for path, content in outputs.items():
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                mismatches.append(path.relative_to(PROJECT_ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    return mismatches


def _print_receipt(outputs: dict[Path, str]) -> None:
    aggregate = json.loads(outputs[AGGREGATE_OUTPUT])
    counts = aggregate["counts"]
    print(
        "mvp_status=verified "
        f"cases={counts['total']} supported={counts['claim_supported']} "
        f"unknown={counts['claim_unknown']} conflict={counts['claim_conflict']} "
        f"policy_violations={counts['policy_violations']} "
        f"false_supported={counts['false_supported']}"
    )
    print(f"aggregate_sha256={sha256_text(outputs[AGGREGATE_OUTPUT])}")
    print(f"aggregate_path={AGGREGATE_OUTPUT.relative_to(PROJECT_ROOT).as_posix()}")


def _serve(port: int) -> int:
    safe_environment = {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in ("API_KEY", "TOKEN", "SECRET"))
    }
    command = [
        sys.executable,
        "-B",
        "-m",
        "streamlit",
        "run",
        str(PROJECT_ROOT / "timeline_app.py"),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    return subprocess.call(command, cwd=PROJECT_ROOT, env=safe_environment)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--generate", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    try:
        outputs = build_outputs()
        mismatches = _write_or_check(outputs, check=not args.generate)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"mvp_status=failed reason={exc}", file=sys.stderr)
        return 1
    if mismatches:
        print(f"mvp_status=failed artifact_mismatch={','.join(mismatches)}")
        return 1
    _print_receipt(outputs)
    if args.generate or args.check:
        return 0
    return _serve(args.port)


if __name__ == "__main__":
    raise SystemExit(main())
