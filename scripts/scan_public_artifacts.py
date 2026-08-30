"""Fail closed on scoped privacy patterns in committed public-facing artifacts."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCANNED_SUFFIXES = {".json", ".jsonl"}
ABSOLUTE_WINDOWS_PATH = re.compile(r"\b[A-Za-z]:[\\/]")
EMAIL_SHAPED = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
SECRET_LIKE = re.compile(r"(?i)\b(?:bearer\s+|sk-)[A-Za-z0-9._-]{8,}")


def tracked_paths(project_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def scan(project_root: Path) -> list[str]:
    findings: list[str] = []
    tracked = tracked_paths(project_root)
    forbidden_names = {".env", ".env.local", ".env.production", "credentials.json", "secrets.json"}
    for relative in tracked:
        if Path(relative).name.lower() in forbidden_names:
            findings.append(f"tracked_sensitive_filename:{relative}")
    artifact_root = project_root / "artifacts"
    for path in sorted(artifact_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        relative = path.relative_to(project_root).as_posix()
        text = path.read_text(encoding="utf-8")
        if ABSOLUTE_WINDOWS_PATH.search(text):
            findings.append(f"absolute_windows_path:{relative}")
        if EMAIL_SHAPED.search(text):
            findings.append(f"email_shaped_text:{relative}")
        if SECRET_LIKE.search(text):
            findings.append(f"secret_like_text:{relative}")
    return findings


def main() -> int:
    argparse.ArgumentParser().parse_args()
    findings = scan(PROJECT_ROOT)
    if findings:
        print("public_artifact_scan=failed")
        for finding in findings:
            print(f"finding={finding}")
        return 1
    print("public_artifact_scan=passed scope=tracked-sensitive-filenames-and-artifact-json-jsonl")
    print("boundary=pattern_scan_not_general_secret_scanning_or_private_data_certification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
