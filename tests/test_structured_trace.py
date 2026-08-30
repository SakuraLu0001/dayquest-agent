from __future__ import annotations

import json
from pathlib import Path

import pytest

from dayquest.agent import run_agent
from dayquest.structured_trace import TRACE_SCHEMA_VERSION, ToolTraceEvent
from scripts.generate_synthetic_trace import ARTIFACT_ID, DEFAULT_OUTPUT, build_trace_text


PROJECT_DATA = Path(__file__).resolve().parents[1] / "data"


def test_local_source_tools_emit_structured_privacy_safe_trace() -> None:
    state = run_agent(PROJECT_DATA, run_id="trace-test-run")

    assert [event.tool for event in state.structured_trace] == [
        "READ_CALENDAR",
        "READ_TRANSACTIONS",
        "READ_EMAILS",
    ]
    assert [event.step_id for event in state.structured_trace] == [
        "trace-test-run:step-001",
        "trace-test-run:step-002",
        "trace-test-run:step-003",
    ]
    assert all(event.schema_version == TRACE_SCHEMA_VERSION for event in state.structured_trace)
    assert all(event.status == "succeeded" for event in state.structured_trace)
    assert all(event.retry_attempt == 0 for event in state.structured_trace)
    assert all(event.error_type is None for event in state.structured_trace)
    assert all(event.latency_ms >= 0 for event in state.structured_trace)

    serialized = json.dumps([event.to_dict() for event in state.structured_trace])
    assert "demo.user@example.com" not in serialized
    assert "DQ-77102" not in serialized
    assert str(PROJECT_DATA) not in serialized


def test_local_source_failure_records_safe_error_type_without_raw_path(tmp_path: Path) -> None:
    state = run_agent(tmp_path, run_id="trace-failure-run")

    assert state.structured_trace
    first = state.structured_trace[0]
    assert first.tool == "READ_CALENDAR"
    assert first.status == "failed"
    assert first.error_type == "data_load_error"
    assert first.output_summary == {"record_count": 0, "result": "unavailable"}
    assert str(tmp_path) not in json.dumps(first.to_dict())


@pytest.mark.parametrize(
    "unsafe_value",
    ["demo.user@example.com", r"D:\private\events.json", "Bearer abcdefghijk"],
)
def test_trace_schema_rejects_private_text_and_absolute_paths(unsafe_value: str) -> None:
    with pytest.raises(ValueError, match="unsafe_trace"):
        ToolTraceEvent(
            schema_version=TRACE_SCHEMA_VERSION,
            run_id="unsafe-test",
            step_id="unsafe-test:step-001",
            iteration=1,
            tool="READ_CALENDAR",
            status="succeeded",
            latency_ms=1,
            retry_attempt=0,
            error_type=None,
            state_transition={"event_count_before": 0, "event_count_after": 1},
            input_summary={"operation": "read", "source": unsafe_value},
            output_summary={"record_count": 1},
        )


def test_committed_synthetic_trace_is_deterministic() -> None:
    first = build_trace_text()
    second = build_trace_text()

    assert first == second
    assert DEFAULT_OUTPUT.read_text(encoding="utf-8") == first
    records = [json.loads(line) for line in first.splitlines()]
    assert {record["run_id"] for record in records} == {ARTIFACT_ID}
    assert [record["latency_ms"] for record in records] == [1, 1, 1]
