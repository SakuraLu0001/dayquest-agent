"""Shared, serializable models for DayQuest."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Action(str, Enum):
    READ_NEXLA_EVENTS = "READ_NEXLA_EVENTS"
    READ_CALENDAR = "READ_CALENDAR"
    READ_TRANSACTIONS = "READ_TRANSACTIONS"
    READ_EMAILS = "READ_EMAILS"
    ANALYZE_TIMELINE = "ANALYZE_TIMELINE"
    REDACT_PRIVATE_DATA = "REDACT_PRIVATE_DATA"
    GENERATE_STORY = "GENERATE_STORY"
    EVALUATE_STORY = "EVALUATE_STORY"
    STOP = "STOP"


@dataclass
class Event:
    event_id: str
    start_time: str
    end_time: str
    event_type: str
    summary: str
    source: str
    confidence: float
    sensitivity: str
    evidence: Any
    redacted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Scene:
    scene_number: int
    title: str
    approximate_time: str
    fictional_event: str
    narration: str
    based_on_event_ids: list[str]
    fictional_embellishment: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TraceEntry:
    iteration: int
    action: str
    observation: str
    decision: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentState:
    goal: str = "Reconstruct a synthetic day and create a privacy-safe fantasy log"
    iteration: int = 0
    max_iterations: int = 5
    available_sources: list[str] = field(
        default_factory=lambda: ["calendar", "transactions", "emails"]
    )
    queried_sources: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    missing_time_ranges: list[str] = field(default_factory=list)
    privacy_risks: dict[str, list[str]] = field(
        default_factory=lambda: {"Detected": [], "Removed": [], "Generalized": []}
    )
    scenes: list[Scene] = field(default_factory=list)
    selected_motif: str = ""
    evaluation: dict[str, Any] = field(default_factory=dict)
    finished: bool = False
    stop_reason: str = ""
    trace: list[TraceEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    provider_status: dict[str, Any] = field(
        default_factory=lambda: {
            "provider": "AkashML",
            "configured": False,
            "attempted": False,
            "connected": False,
            "used_for_story": False,
            "model": "",
            "http_status": None,
            "latency_ms": None,
            "request_id": None,
            "fallback_used": True,
            "error_type": None,
            "fallback_reason": None,
            "remote_scene_count": None,
            "remote_artifact_type": None,
        }
    )
    nexla_status: dict[str, Any] = field(
        default_factory=lambda: {
            "provider": "Nexla",
            "configured": False,
            "attempted": False,
            "connected": False,
            "used_for_timeline": False,
            "nexset_id": "",
            "record_count": None,
            "raw_sample_count": None,
            "deduplicated_record_count": None,
            "latency_ms": None,
            "http_status": None,
            "fallback_used": True,
            "error_type": None,
        }
    )
