"""One-shot, privacy-safe Nexla transformed Nexset check."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dayquest.nexla_client import NexlaClient, NexlaClientError  # noqa: E402


def main() -> int:
    started = time.perf_counter()
    exit_code = 1
    client: NexlaClient | None = None
    result = {
        "status": "failure",
        "http_status": None,
        "nexset_id": "not set",
        "record_count": None,
        "latency_ms": 0,
        "error_type": "connect_error",
    }
    try:
        client = NexlaClient.from_env(PROJECT_ROOT / ".env")
        result["nexset_id"] = client.config.nexset_id or "not set"
        samples = client.fetch_normalized_events()
        result = {
            "status": "success",
            "http_status": samples.http_status,
            "nexset_id": samples.nexset_id,
            "record_count": samples.record_count,
            "latency_ms": samples.latency_ms,
            "error_type": None,
        }
        exit_code = 0
    except NexlaClientError as exc:
        latency_ms = exc.diagnostics.latency_ms
        if latency_ms is None:
            latency_ms = round((time.perf_counter() - started) * 1000)
        result = {
            "status": "failure",
            "http_status": exc.diagnostics.http_status,
            "nexset_id": client.config.nexset_id if client and client.config.nexset_id else "not set",
            "record_count": None,
            "latency_ms": latency_ms,
            "error_type": exc.error_type,
        }
    except Exception:
        result["latency_ms"] = round((time.perf_counter() - started) * 1000)
    finally:
        print(json.dumps(result, ensure_ascii=True), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
