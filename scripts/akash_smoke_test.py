"""One-shot, privacy-safe AkashML connectivity check."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dayquest.akash_client import AkashClientError, AkashStoryClient  # noqa: E402
from dayquest.models import Event  # noqa: E402


def _synthetic_events() -> list[Event]:
    common = {
        "source": "synthetic_smoke_test",
        "confidence": 1.0,
        "sensitivity": "low",
        "evidence": {"status": "synthetic and withheld"},
        "redacted": True,
    }
    return [
        Event(
            event_id="smoke-local-1",
            start_time="2026-01-01T09:00",
            end_time="2026-01-01T10:00",
            event_type="language_exam",
            summary="A morning language certification activity at a generalized venue.",
            **common,
        ),
        Event(
            event_id="smoke-local-2",
            start_time="2026-01-01T12:00",
            end_time="2026-01-01T12:20",
            event_type="travel",
            summary="Travel by local transit toward the event venue.",
            **common,
        ),
        Event(
            event_id="smoke-local-3",
            start_time="2026-01-01T14:00",
            end_time="2026-01-01T17:00",
            event_type="hackathon",
            summary="An afternoon AI agent building event at a generalized venue.",
            **common,
        ),
    ]


def main() -> int:
    started = time.perf_counter()
    exit_code = 1
    client: AkashStoryClient | None = None
    output = {
        "status": "failure",
        "model": "not set",
        "http_status": None,
        "artifact_type": "motif_code",
        "selected_motif": None,
        "latency_ms": 0,
        "error_type": "unexpected_error",
    }
    try:
        client = AkashStoryClient.from_env(PROJECT_ROOT / ".env")
        output["model"] = client.config.model or "not set"
        motif_result = client.select_fantasy_motif(
            _synthetic_events(),
            max_completion_tokens=16,
        )
        output = {
            "status": "success",
            "model": motif_result.model,
            "http_status": motif_result.http_status,
            "artifact_type": "motif_code",
            "selected_motif": motif_result.motif_code,
            "latency_ms": motif_result.latency_ms,
            "error_type": None,
        }
        exit_code = 0
    except AkashClientError as exc:
        diagnostics = exc.diagnostics
        latency_ms = diagnostics.latency_ms
        if latency_ms is None:
            latency_ms = round((time.perf_counter() - started) * 1000)
        output = {
            "status": "failure",
            "model": client.config.model if client and client.config.model else "not set",
            "http_status": diagnostics.http_status,
            "artifact_type": "motif_code",
            "selected_motif": None,
            "latency_ms": latency_ms,
            "error_type": exc.error_type,
        }
    except Exception:
        output["latency_ms"] = round((time.perf_counter() - started) * 1000)
        output["error_type"] = "unexpected_error"
    finally:
        print(json.dumps(output, ensure_ascii=True), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
