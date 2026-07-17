from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

import dayquest.pomerium_mcp_server as gateway
from dayquest.models import Event
from dayquest.nexla_client import NexlaClientError


TEST_SECRET = "unit-test-token-never-return"


def _event(
    event_id: str = "internal-event-id",
    start_time: str = "2026-07-17T10:00:00-07:00",
    summary: str = "A safe synthetic development milestone.",
) -> Event:
    return Event(
        event_id=event_id,
        start_time=start_time,
        end_time=start_time,
        event_type="agent_milestone",
        summary=summary,
        source="developer_activity",
        confidence=1.0,
        sensitivity="low",
        evidence={"private": TEST_SECRET},
        redacted=True,
    )


def test_only_three_expected_tools_are_registered() -> None:
    tools = asyncio.run(gateway.mcp.list_tools())

    assert {tool.name for tool in tools} == {
        "get_safe_day_events",
        "get_dayquest_privacy_contract",
        "get_dayquest_status",
    }


@pytest.mark.parametrize("limit", [0, -1])
def test_limit_below_one_is_rejected(limit: int) -> None:
    with pytest.raises(gateway.SafeGatewayError, match="invalid_limit"):
        gateway._serialize_safe_events([_event()], limit)


@pytest.mark.parametrize("limit", [11, 100])
def test_limit_above_ten_is_rejected(limit: int) -> None:
    with pytest.raises(gateway.SafeGatewayError, match="invalid_limit"):
        gateway._serialize_safe_events([_event()], limit)


def test_safe_events_contain_only_allowlisted_fields() -> None:
    records = gateway._serialize_safe_events([_event()], 1)

    assert set(records[0]) == gateway.SAFE_EVENT_FIELDS
    assert records[0]["safe_event_id"] == "safe-event-1"
    assert records[0]["redacted"] is True


def test_internal_id_and_evidence_are_never_returned() -> None:
    records = gateway._serialize_safe_events([_event()], 1)
    serialized = repr(records)

    assert "internal-event-id" not in serialized
    assert "evidence" not in serialized
    assert TEST_SECRET not in serialized


def test_private_email_amount_order_and_address_are_removed() -> None:
    unsafe_summary = (
        "Contact private.person@example.com after paying $91.27 for order DQ-48291 "
        "at 123 Main Street."
    )

    records = gateway._serialize_safe_events([_event(summary=unsafe_summary)], 1)
    safe_summary = records[0]["safe_summary"]

    assert "private.person@example.com" not in safe_summary
    assert "$91.27" not in safe_summary
    assert "DQ-48291" not in safe_summary
    assert "123 Main Street" not in safe_summary
    assert "[REDACTED_EMAIL]" not in safe_summary
    assert "[REDACTED_ORDER]" not in safe_summary


def test_events_are_limited_and_keep_chronological_order() -> None:
    events = [
        _event("event-3", "2026-07-17T12:00:00-07:00"),
        _event("event-1", "2026-07-17T09:00:00-07:00"),
        _event("event-2", "2026-07-17T11:00:00-07:00"),
    ]

    records = gateway._serialize_safe_events(events, 2)

    assert [record["approximate_time"] for record in records] == [
        "morning",
        "morning",
    ]
    assert [record["safe_event_id"] for record in records] == [
        "safe-event-1",
        "safe-event-2",
    ]


def test_duplicate_internal_ids_are_removed_before_safe_id_assignment() -> None:
    records = gateway._serialize_safe_events(
        [_event("same-id"), _event("same-id"), _event("other-id")],
        8,
    )

    assert len(records) == 2
    assert [record["safe_event_id"] for record in records] == [
        "safe-event-1",
        "safe-event-2",
    ]


def test_nexla_failure_uses_safe_local_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingNexlaClient:
        configured = True

        def fetch_normalized_events(self) -> object:
            raise NexlaClientError("authentication_or_expired_token")

    fallback = [_event("fallback-event")]
    monkeypatch.setattr(gateway, "_load_local_demo_events", lambda _path=None: fallback)

    events = gateway._load_preferred_events(  # type: ignore[arg-type]
        nexla_client=FailingNexlaClient()
    )

    assert events == fallback


def test_privacy_contract_blocks_raw_data() -> None:
    contract = gateway.get_dayquest_privacy_contract()

    assert contract["raw_data_exposed"] is False
    assert "event_id" in contract["blocked_fields"]
    assert "evidence" in contract["blocked_fields"]
    assert set(contract["allowed_fields"]) == gateway.SAFE_EVENT_FIELDS


def test_server_is_fixed_to_localhost_streamable_http() -> None:
    assert gateway.MCP_ENDPOINT == "http://127.0.0.1:8080/mcp"
    assert gateway.mcp.settings.host == "127.0.0.1"
    assert gateway.mcp.settings.port == 8080
    assert gateway.mcp.settings.streamable_http_path == "/mcp"
    assert gateway.mcp.settings.stateless_http is True
    assert gateway.mcp.settings.json_response is True


def test_status_contains_no_credentials_or_local_paths() -> None:
    status = gateway.get_dayquest_status()
    serialized = repr(status).lower()

    assert set(status) == {
        "service",
        "mcp_transport",
        "privacy_mode",
        "akash_role",
        "nexla_role",
    }
    for forbidden in ("api_key", "token", "authorization", "headers", "path"):
        assert forbidden not in serialized


def test_tool_failure_returns_only_safe_error_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_safely() -> list[Event]:
        raise RuntimeError(TEST_SECRET)

    monkeypatch.setattr(gateway, "_load_preferred_events", fail_safely)

    with pytest.raises(ToolError) as caught:
        gateway.get_safe_day_events(limit=3)

    assert str(caught.value) == "provider_error"
    assert TEST_SECRET not in str(caught.value)


def test_no_forbidden_read_write_or_admin_tools_exist() -> None:
    tool_names = {tool.name for tool in asyncio.run(gateway.mcp.list_tools())}

    assert not any(
        name.startswith(("get_raw", "read_", "write_", "delete_", "admin_"))
        for name in tool_names
    )
