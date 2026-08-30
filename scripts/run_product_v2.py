"""Generate, verify, or serve the deterministic Product V2 evidence replay."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dayquest.evaluation import canonical_json  # noqa: E402
from dayquest.product_v2 import build_product_v2, product_v2_identity  # noqa: E402


OUTPUT = PROJECT_ROOT / "artifacts" / "product_v2" / "replay_demo.json"


def build_output() -> tuple[dict, str]:
    artifact = build_product_v2(PROJECT_ROOT)
    return artifact, canonical_json(artifact)


def _serve(port: int) -> int:
    safe_environment = {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in ("API_KEY", "TOKEN", "SECRET"))
    }
    return subprocess.call(
        [
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
        ],
        cwd=PROJECT_ROOT,
        env=safe_environment,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--generate", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    try:
        first, content = build_output()
        second, second_content = build_output()
    except (OSError, ValueError, KeyError) as exc:
        print(f"product_v2_status=failed reason={exc}", file=sys.stderr)
        return 1
    if content != second_content:
        print("product_v2_status=failed reason=two_build_identity_mismatch", file=sys.stderr)
        return 1
    if args.generate:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    elif not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != content:
        print("product_v2_status=failed reason=committed_artifact_mismatch", file=sys.stderr)
        return 1
    counts = first["transition_counts"]
    print(
        "product_v2_status=verified "
        f"replays={len(first['replays'])} "
        f"supported_to_unknown={counts['Supported->Unknown']} "
        f"unknown_to_supported={counts['Unknown->Supported']} "
        f"conflict_to_unknown={counts['Conflict->Unknown']}"
    )
    print(f"product_v2_sha256={product_v2_identity(first)}")
    print(f"artifact_path={OUTPUT.relative_to(PROJECT_ROOT).as_posix()}")
    if args.generate or args.check:
        return 0
    return _serve(args.port)


if __name__ == "__main__":
    raise SystemExit(main())
