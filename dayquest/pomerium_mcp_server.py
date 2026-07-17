"""Local, read-only MCP gateway for privacy-safe DayQuest summaries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from .data_loader import DataLoadError, load_calendar, load_emails, load_transactions
from .models import Event
from .nexla_client import NexlaClient, NexlaClientError
from .privacy import contains_forbidden_data, redact_events, redact_text


MCP_HOST = "127.0.0.1"
MCP_PORT = 8080
MCP_PATH = "/mcp"
MCP_ENDPOINT = f"http://{MCP_HOST}:{MCP_PORT}{MCP_PATH}"
MIN_LIMIT = 1
MAX_LIMIT = 10
SAFE_EVENT_FIELDS = {
    "safe_event_id",
    "approximate_time",
    "event_type",
    "safe_summary",
    "source",
    "sensitivity",
    "redacted",
}
BLOCKED_FIELDS = [
    "event_id",
    "evidence",
    "email_body",
    "phone",
    "address",
    "amount",
    "order_id",
    "api_key",
    "token",
    "headers",
    "metadata",
]


class SafeGatewayError(RuntimeError):
    """Categorized error that carries no provider or private response content."""

    def __init__(self, error_type: str) -> None:
        self.error_type = error_type
        super().__init__(error_type)


def _validate_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise SafeGatewayError("invalid_limit")
    if not MIN_LIMIT <= limit <= MAX_LIMIT:
        raise SafeGatewayError("invalid_limit")
    return limit


def _approximate_time(iso_time: str) -> str:
    try:
        hour = int(iso_time[11:13])
    except (TypeError, ValueError, IndexError) as exc:
        raise SafeGatewayError("invalid_event_time") from exc
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def _deduplicate_events(events: list[Event]) -> list[Event]:
    unique: dict[str, Event] = {}
    for event in events:
        unique.setdefault(event.event_id, event)
    return sorted(unique.values(), key=lambda event: event.start_time)


def _load_local_demo_events(data_dir: Path | None = None) -> list[Event]:
    base_dir = data_dir or Path(__file__).resolve().parent.parent / "data"
    events: list[Event] = []
    for loader in (load_calendar, load_transactions, load_emails):
        try:
            events.extend(loader(base_dir))
        except DataLoadError:
            continue
    if not events:
        raise SafeGatewayError("local_fallback_unavailable")
    safe_events, _ = redact_events(events)
    return _deduplicate_events(safe_events)


def _load_preferred_events(
    nexla_client: NexlaClient | None = None,
    data_dir: Path | None = None,
) -> list[Event]:
    client = nexla_client or NexlaClient.from_env()
    if client.configured:
        try:
            result = client.fetch_normalized_events()
        except NexlaClientError:
            pass
        else:
            if result.events:
                return _deduplicate_events(result.events)
    return _load_local_demo_events(data_dir)


def _safe_summary(summary: str) -> str:
    safe = redact_text(summary)
    for marker in ("[REDACTED_EMAIL]", "[REDACTED_PHONE]", "[REDACTED_ORDER]"):
        safe = safe.replace(marker, "[REDACTED]")
    safe = " ".join(safe.split())
    if not safe or contains_forbidden_data(safe):
        raise SafeGatewayError("privacy_validation_failed")
    return safe


def _serialize_safe_events(events: list[Event], limit: int) -> list[dict[str, Any]]:
    checked_limit = _validate_limit(limit)
    safe_records: list[dict[str, Any]] = []
    for event in _deduplicate_events(events)[:checked_limit]:
        sensitivity = (
            event.sensitivity
            if event.sensitivity in {"low", "medium", "high", "redacted"}
            else "redacted"
        )
        record = {
            "safe_event_id": f"safe-event-{len(safe_records) + 1}",
            "approximate_time": _approximate_time(event.start_time),
            "event_type": event.event_type,
            "safe_summary": _safe_summary(event.summary),
            "source": event.source,
            "sensitivity": sensitivity,
            "redacted": True,
        }
        if set(record) != SAFE_EVENT_FIELDS:
            raise SafeGatewayError("safe_schema_failed")
        safe_records.append(record)
    if not safe_records:
        raise SafeGatewayError("safe_data_unavailable")
    return safe_records


mcp = FastMCP(
    "DayQuest Privacy Gateway",
    host=MCP_HOST,
    port=MCP_PORT,
    streamable_http_path=MCP_PATH,
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def get_safe_day_events(limit: int = 8) -> list[dict[str, Any]]:
    """Return chronological, privacy-safe DayQuest event summaries."""
    try:
        return _serialize_safe_events(_load_preferred_events(), limit)
    except SafeGatewayError as exc:
        raise ToolError(exc.error_type) from None
    except Exception:
        raise ToolError("provider_error") from None


@mcp.tool()
def get_dayquest_privacy_contract() -> dict[str, Any]:
    """Describe the fixed privacy boundary of this read-only MCP service."""
    return {
        "raw_data_exposed": False,
        "allowed_fields": sorted(SAFE_EVENT_FIELDS),
        "blocked_fields": BLOCKED_FIELDS,
        "gateway_role": "Pomerium authenticates and authorizes remote MCP access",
    }


@mcp.tool()
def get_dayquest_status() -> dict[str, str]:
    """Return public roles and transport status without configuration details."""
    return {
        "service": "DayQuest Privacy Gateway",
        "mcp_transport": "streamable-http",
        "privacy_mode": "safe summaries only",
        "akash_role": "fantasy motif selection",
        "nexla_role": "event normalization",
    }


def main() -> None:
    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
