"""Generate the deterministic, no-key DayQuest structured trace artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dayquest.agent import run_agent  # noqa: E402


ARTIFACT_ID = "dayquest-synthetic-baseline-v1"
DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts" / "traces" / f"{ARTIFACT_ID}.jsonl"


class DeterministicClock:
    """Return fixed 1 ms intervals so the committed artifact is byte-stable."""

    def __init__(self) -> None:
        self._tick = 0

    def __call__(self) -> float:
        self._tick += 1
        return self._tick / 1000


def build_trace_text() -> str:
    state = run_agent(
        PROJECT_ROOT / "data",
        run_id=ARTIFACT_ID,
        trace_clock=DeterministicClock(),
    )
    if not state.finished or not state.evaluation.get("passed"):
        raise RuntimeError("synthetic_baseline_did_not_pass")
    records = [
        json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for event in state.structured_trace
    ]
    return "\n".join(records) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    content = build_trace_text()
    output = args.output.resolve()
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != content:
            print(f"artifact_mismatch: {output}")
            return 1
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8", newline="\n")

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest().upper()
    print(f"artifact_id={ARTIFACT_ID}")
    print(f"records={len(content.splitlines())}")
    print(f"sha256={digest}")
    print(f"path={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
