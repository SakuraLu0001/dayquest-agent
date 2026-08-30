"""Privacy-safe structured tool-call traces for DayQuest."""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable
from uuid import uuid4


TRACE_SCHEMA_VERSION = "dayquest.tool_trace.v1"
TRACE_STATUS_VALUES = {"succeeded", "failed"}
_ABSOLUTE_WINDOWS_PATH = re.compile(r"\b[A-Za-z]:[\\/]")
_SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?<!\w)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\w)"),
    re.compile(r"\$\s?\d+(?:\.\d{2})?"),
    re.compile(r"(?i)\b(?:bearer\s+|sk-)[A-Za-z0-9._-]{8,}"),
)
_FORBIDDEN_KEY_PARTS = {
    "address",
    "api_key",
    "authorization",
    "body",
    "credential",
    "email",
    "evidence",
    "headers",
    "local_path",
    "order_id",
    "payload",
    "phone",
    "secret",
    "session_token",
    "token",
}


def _validate_safe_summary(value: Any, *, key_path: str = "summary") -> None:
    """Reject trace summaries that could expose private payloads or local paths."""
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).lower()
            if any(part in normalized_key for part in _FORBIDDEN_KEY_PARTS):
                raise ValueError(f"unsafe_trace_summary_key:{key_path}.{key}")
            _validate_safe_summary(item, key_path=f"{key_path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_safe_summary(item, key_path=f"{key_path}[{index}]")
        return
    if isinstance(value, str):
        if _ABSOLUTE_WINDOWS_PATH.search(value):
            raise ValueError(f"unsafe_trace_absolute_path:{key_path}")
        if any(pattern.search(value) for pattern in _SENSITIVE_TEXT_PATTERNS):
            raise ValueError(f"unsafe_trace_private_text:{key_path}")


@dataclass(frozen=True)
class ToolTraceEvent:
    """One auditable, privacy-safe tool call in a DayQuest run."""

    schema_version: str
    run_id: str
    step_id: str
    iteration: int
    tool: str
    status: str
    latency_ms: int
    retry_attempt: int
    error_type: str | None
    state_transition: dict[str, int]
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]

    def __post_init__(self) -> None:
        if self.schema_version != TRACE_SCHEMA_VERSION:
            raise ValueError("unsupported_trace_schema")
        if not self.run_id or not self.step_id or not self.tool:
            raise ValueError("trace_identity_required")
        if self.status not in TRACE_STATUS_VALUES:
            raise ValueError("invalid_trace_status")
        if self.latency_ms < 0 or self.retry_attempt < 0:
            raise ValueError("invalid_trace_measurement")
        _validate_safe_summary(self.input_summary, key_path="input_summary")
        _validate_safe_summary(self.output_summary, key_path="output_summary")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ToolTraceRecorder:
    """Assign stable step identities and record sanitized tool summaries."""

    def __init__(
        self,
        *,
        run_id: str | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.run_id = run_id or f"run-{uuid4().hex}"
        self.clock = clock or time.perf_counter
        self.events: list[ToolTraceEvent] = []

    def start(self) -> float:
        return self.clock()

    def record(
        self,
        *,
        iteration: int,
        tool: str,
        started_at: float,
        status: str,
        error_type: str | None,
        state_transition: dict[str, int],
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        retry_attempt: int = 0,
    ) -> ToolTraceEvent:
        step_number = len(self.events) + 1
        latency_ms = max(0, round((self.clock() - started_at) * 1000))
        event = ToolTraceEvent(
            schema_version=TRACE_SCHEMA_VERSION,
            run_id=self.run_id,
            step_id=f"{self.run_id}:step-{step_number:03d}",
            iteration=iteration,
            tool=tool,
            status=status,
            latency_ms=latency_ms,
            retry_attempt=retry_attempt,
            error_type=error_type,
            state_transition=state_transition,
            input_summary=input_summary,
            output_summary=output_summary,
        )
        self.events.append(event)
        return event
