from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from dayquest.agent import deduplicate_events, run_agent
from dayquest.akash_client import AkashMotifResult
from dayquest.models import Event
from dayquest.nexla_client import (
    NexlaClient,
    NexlaClientError,
    NexlaConfig,
    normalized_record_to_event,
)
from dayquest.story import (
    canonical_event_category,
    generate_local_scenes,
    is_story_event,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_DATA = PROJECT_ROOT / "data"
TEST_TOKEN = "unit-test-nexla-token-never-store"


def _records() -> list[dict[str, object]]:
    return [
        {
            "event_id": "nexla-hackathon-arrival",
            "start_time": "2026-07-17T09:30:00-07:00",
            "end_time": "2026-07-17T10:00:00-07:00",
            "event_type": "hackathon",
            "summary": "Arrived at a generalized AI agent hackathon venue.",
            "source": "calendar",
            "confidence": 0.95,
            "sensitivity": "low",
            "redacted": True,
        },
        {
            "event_id": "nexla-transit",
            "start_time": "2026-07-17T10:10:00-07:00",
            "end_time": "",
            "event_type": "travel",
            "summary": "Moved through the event venue toward the kickoff session.",
            "source": "email_metadata",
            "confidence": 0.8,
            "sensitivity": "medium",
            "redacted": True,
        },
        {
            "event_id": "nexla-build",
            "start_time": "2026-07-17T11:20:00-07:00",
            "end_time": "2026-07-17T12:40:00-07:00",
            "event_type": "coffee",
            "summary": "Paused for modest provisions while creating the DayQuest project.",
            "source": "developer_activity",
            "confidence": 1.0,
            "sensitivity": "low",
            "redacted": True,
        },
    ]


def _normalized_day_records() -> list[dict[str, object]]:
    definitions = [
        ("confirmation", "2026-07-17T08:15:00-07:00", "event_confirmation", "Registration for the public event was confirmed.", "email_metadata"),
        ("arrival", "2026-07-17T09:30:00-07:00", "calendar_event", "Arrived at a generalized AI agent event venue.", "calendar"),
        ("kickoff", "2026-07-17T10:00:00-07:00", "calendar_event", "Attended a kickoff and sponsor presentation session.", "calendar"),
        ("repository", "2026-07-17T11:20:00-07:00", "repository_created", "Created the DayQuest project repository.", "developer_activity"),
        ("agent-loop", "2026-07-17T12:10:00-07:00", "agent_milestone", "Completed an observation-driven local agent loop.", "developer_activity"),
        ("tests", "2026-07-17T12:35:00-07:00", "test_result", "Automated tests passed successfully.", "developer_activity"),
        ("ui-fix", "2026-07-17T12:50:00-07:00", "bug_fix", "Fixed an interface rendering issue.", "developer_activity"),
        ("integration", "2026-07-17T14:00:00-07:00", "sponsor_integration", "Connected an external model for fantasy motif selection.", "developer_activity"),
    ]
    return [
        {
            "event_id": f"nexla-{event_id}",
            "start_time": start_time,
            "end_time": "",
            "event_type": event_type,
            "summary": summary,
            "source": source,
            "confidence": 1.0,
            "sensitivity": "low",
            "redacted": True,
        }
        for event_id, start_time, event_type, summary, source in definitions
    ]


class FakeMotifClient:
    configured = True
    configuration_error = None
    config = SimpleNamespace(model="fake-motif-model")

    def __init__(self) -> None:
        self.calls = 0

    def select_fantasy_motif(self, _events: list[Event]) -> AkashMotifResult:
        self.calls += 1
        return AkashMotifResult(
            motif_code="CLOCKWORK_TRIAL",
            model="fake-motif-model",
            http_status=200,
            latency_ms=10,
            request_id="fake-request",
        )


class FakeResponse:
    def __init__(self, payload: object, status_code: int = 200, invalid_json: bool = False) -> None:
        self.payload = payload
        self.status_code = status_code
        self.invalid_json = invalid_json

    def json(self) -> object:
        if self.invalid_json:
            raise ValueError("safe fake invalid JSON")
        return self.payload


class FakeHttpClient:
    def __init__(self, response: FakeResponse, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.url: str | None = None
        self.kwargs: dict[str, object] | None = None
        self.calls = 0

    def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls += 1
        self.url = url
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


def _client(
    payload: object | None = None,
    *,
    status_code: int = 200,
    error: Exception | None = None,
    invalid_json: bool = False,
) -> tuple[NexlaClient, FakeHttpClient]:
    response = FakeResponse(_records() if payload is None else payload, status_code, invalid_json)
    transport = FakeHttpClient(response, error=error)
    client = NexlaClient(
        NexlaConfig(
            api_host="https://unit-test.invalid",
            session_token=TEST_TOKEN,
            nexset_id="435637",
            timeout_seconds=3,
        ),
        client=transport,
    )
    return client, transport


def test_missing_config_uses_existing_local_fallback() -> None:
    client = NexlaClient(NexlaConfig())

    state = run_agent(PROJECT_DATA, nexla_client=client)

    assert state.nexla_status["configured"] is False
    assert state.nexla_status["attempted"] is False
    assert state.nexla_status["connected"] is False
    assert state.nexla_status["used_for_timeline"] is False
    assert state.nexla_status["error_type"] == "missing_config"
    assert "calendar" in state.queried_sources
    assert state.evaluation["passed"] is True


def test_http_200_valid_samples_are_converted_without_metadata() -> None:
    client, transport = _client()

    result = client.fetch_normalized_events()

    assert result.http_status == 200
    assert result.nexset_id == "435637"
    assert result.raw_sample_count == 3
    assert result.record_count == 3
    assert len(result.events) == 3
    assert result.events[1].end_time == result.events[1].start_time
    assert result.events[0].evidence == {
        "status": "normalized event; Nexla metadata not retained"
    }
    assert transport.calls == 1
    assert transport.url == "https://unit-test.invalid/data_sets/435637/samples"
    assert transport.kwargs is not None
    assert transport.kwargs["params"] == {
        "count": 20,
        "include_metadata": "false",
        "live": "false",
    }
    assert TEST_TOKEN not in repr(result)


def test_data_wrapper_is_accepted_without_storing_wrapper_metadata() -> None:
    client, _ = _client({"data": _records()})

    result = client.fetch_normalized_events()

    assert result.record_count == 3
    assert all("data" not in event.evidence for event in result.events)


@pytest.mark.parametrize("array_key", ["records", "samples", "items"])
def test_named_top_level_sample_arrays_are_accepted(array_key: str) -> None:
    client, _ = _client({array_key: _records(), "request_metadata": "ignored"})

    result = client.fetch_normalized_events()

    assert result.record_count == 3


@pytest.mark.parametrize("record_key", ["output", "data", "value"])
def test_record_wrappers_and_metadata_are_ignored(record_key: str) -> None:
    wrapped = [
        {
            record_key: {**record, "location": "ignored raw location"},
            "metadata": {"owner_id": "ignored-owner"},
            "input": {"body": "ignored input body"},
        }
        for record in _records()
    ]
    client, _ = _client(wrapped)

    result = client.fetch_normalized_events()

    assert result.record_count == 3
    serialized_events = repr(result.events)
    assert "ignored raw location" not in serialized_events
    assert "ignored-owner" not in serialized_events
    assert "ignored input body" not in serialized_events


def test_nested_output_data_wrapper_is_unwrapped() -> None:
    wrapped = [
        {
            "input": {"data": {"body": "ignored source body"}},
            "output": {
                "data": {**record, "nexla_metadata": "ignored metadata"},
                "metadata": {"data_set_id": "ignored dataset"},
            },
        }
        for record in _records()
    ]
    client, _ = _client(wrapped)

    result = client.fetch_normalized_events()

    assert result.record_count == 3
    serialized_events = repr(result.events)
    assert "ignored source body" not in serialized_events
    assert "ignored metadata" not in serialized_events
    assert "ignored dataset" not in serialized_events


def test_nested_output_list_is_flattened() -> None:
    wrapped = [{"output": [{"value": record}], "metadata": {}} for record in _records()]
    client, _ = _client(wrapped)

    result = client.fetch_normalized_events()

    assert result.record_count == 3


def test_unknown_nested_output_wrapper_is_safely_traversed() -> None:
    wrapped = [
        {
            "input": {"private_source_field": "must not be considered"},
            "output": {"transform_result": {"normalized": _records()[0]}},
            "metadata": {"owner_id": "ignored"},
        }
    ]
    client, _ = _client(wrapped)

    result = client.fetch_normalized_events()

    assert result.record_count == 1
    assert result.events[0].event_id == _records()[0]["event_id"]


def test_401_is_safely_classified() -> None:
    client, _ = _client(status_code=401)

    with pytest.raises(NexlaClientError) as caught:
        client.fetch_normalized_events()

    assert caught.value.error_type == "authentication_or_expired_token"
    assert caught.value.diagnostics.http_status == 401
    assert TEST_TOKEN not in str(caught.value)


def test_empty_samples_are_rejected() -> None:
    client, _ = _client([])

    with pytest.raises(NexlaClientError) as caught:
        client.fetch_normalized_events()

    assert caught.value.error_type == "empty_samples"


def test_invalid_json_is_safely_classified() -> None:
    client, _ = _client(invalid_json=True)

    with pytest.raises(NexlaClientError) as caught:
        client.fetch_normalized_events()

    assert caught.value.error_type == "invalid_json"


def test_redacted_false_is_rejected() -> None:
    records = _records()
    records[0]["redacted"] = False
    client, _ = _client(records)

    with pytest.raises(NexlaClientError) as caught:
        client.fetch_normalized_events()

    assert caught.value.error_type == "invalid_schema"


@pytest.mark.parametrize("raw_field", ["location", "body", "email_address", "account_id"])
def test_extra_raw_fields_are_ignored_and_never_enter_event(raw_field: str) -> None:
    record = _records()[0]
    record[raw_field] = "private raw value"

    event = normalized_record_to_event(record)

    assert "private raw value" not in repr(event)
    assert raw_field not in event.evidence


def test_all_nine_allowlisted_fields_are_extracted() -> None:
    record = _records()[0]
    event = normalized_record_to_event(record)

    assert event.event_id == record["event_id"]
    assert event.start_time == record["start_time"]
    assert event.end_time == record["end_time"]
    assert event.event_type == record["event_type"]
    assert event.summary == record["summary"]
    assert event.source == record["source"]
    assert event.confidence == record["confidence"]
    assert event.sensitivity == record["sensitivity"]
    assert event.redacted is True


def test_missing_required_field_is_still_rejected() -> None:
    record = _records()[0]
    del record["summary"]

    with pytest.raises(NexlaClientError) as caught:
        normalized_record_to_event(record)

    assert caught.value.error_type == "invalid_schema"


def test_private_summary_is_rejected_by_local_privacy_check() -> None:
    record = _records()[0]
    record["summary"] = "Contact private.person@example.com"

    with pytest.raises(NexlaClientError) as caught:
        normalized_record_to_event(record)

    assert caught.value.error_type == "invalid_schema"


def test_token_and_record_values_never_enter_error_diagnostics() -> None:
    record = _records()[0]
    record["metadata"] = "unique-private-record-value"
    del record["event_id"]
    client, _ = _client([{"output": record, "metadata": {"token": TEST_TOKEN}}])

    with pytest.raises(NexlaClientError) as caught:
        client.fetch_normalized_events()

    assert caught.value.error_type == "invalid_schema"
    diagnostics = repr(caught.value.diagnostics)
    assert TEST_TOKEN not in diagnostics
    assert "unique-private-record-value" not in diagnostics


def test_nexla_success_is_used_for_final_timeline() -> None:
    client, _ = _client()

    state = run_agent(PROJECT_DATA, nexla_client=client)

    assert state.finished is True
    assert state.evaluation["passed"] is True
    assert state.nexla_status["connected"] is True
    assert state.nexla_status["used_for_timeline"] is True
    assert state.nexla_status["record_count"] == 3
    assert state.nexla_status["raw_sample_count"] == 3
    assert state.nexla_status["deduplicated_record_count"] == 3
    assert state.nexla_status["http_status"] == 200
    assert state.nexla_status["fallback_used"] is False
    assert state.queried_sources == ["nexla"]
    assert {event.event_id for event in state.events} == {
        "nexla-hackathon-arrival",
        "nexla-transit",
        "nexla-build",
    }
    assert {event.source for event in state.events} == {
        "calendar",
        "email_metadata",
        "developer_activity",
    }
    assert any(
        "Loaded 3 Nexla samples and deduplicated them to 3 unique normalized events"
        in entry.observation
        for entry in state.trace
    )


def test_duplicate_nexla_events_are_deduplicated_in_time_order() -> None:
    records = _normalized_day_records()
    client, _ = _client(records + list(reversed(records)))
    motif_client = FakeMotifClient()

    state = run_agent(
        PROJECT_DATA,
        nexla_client=client,
        story_client=motif_client,  # type: ignore[arg-type]
    )

    assert state.nexla_status["raw_sample_count"] == 16
    assert state.nexla_status["deduplicated_record_count"] == 8
    assert state.nexla_status["record_count"] == 8
    assert len(state.events) == 8
    assert len({event.event_id for event in state.events}) == 8
    assert [event.start_time for event in state.events] == sorted(
        event.start_time for event in state.events
    )
    assert state.evaluation["passed"] is True
    assert 3 <= len(state.scenes) <= 5
    assert motif_client.calls == 1
    assert state.provider_status["connected"] is True
    assert state.provider_status["used_for_story"] is True
    assert not any(
        "nexla-confirmation" in scene.based_on_event_ids for scene in state.scenes
    )


@pytest.mark.parametrize(
    ("event_type", "category", "is_core"),
    [
        ("calendar_event", "scheduled_event", True),
        ("repository_created", "build_milestone", True),
        ("agent_milestone", "build_milestone", True),
        ("test_result", "validation_milestone", True),
        ("bug_fix", "challenge_resolution", True),
        ("sponsor_integration", "integration_milestone", True),
        ("event_confirmation", "supporting_evidence", False),
    ],
)
def test_nexla_event_types_map_to_expected_story_categories(
    event_type: str,
    category: str,
    is_core: bool,
) -> None:
    event = Event(
        event_id=f"test-{event_type}",
        start_time="2026-07-17T10:00:00-07:00",
        end_time="2026-07-17T10:00:00-07:00",
        event_type=event_type,
        summary="A safe synthetic event summary.",
        source="developer_activity",
        confidence=1.0,
        sensitivity="low",
        evidence={},
        redacted=True,
    )

    assert canonical_event_category(event_type) == category
    assert is_story_event(event) is is_core


def test_minimum_three_story_events_is_not_lowered() -> None:
    events = [normalized_record_to_event(record) for record in _normalized_day_records()[1:3]]

    assert generate_local_scenes(events) == []


def test_deduplication_keeps_first_event_for_each_id() -> None:
    records = _normalized_day_records()[1:4]
    events = [normalized_record_to_event(record) for record in records]
    duplicate = normalized_record_to_event({**records[0], "summary": "A later duplicate summary."})

    deduplicated = deduplicate_events([events[2], events[0], duplicate, events[1]])

    assert len(deduplicated) == 3
    assert [event.start_time for event in deduplicated] == sorted(
        event.start_time for event in deduplicated
    )
    assert next(
        event for event in deduplicated if event.event_id == events[0].event_id
    ).summary == events[0].summary


def test_nexla_failure_uses_local_fallback_without_crashing() -> None:
    client, _ = _client(status_code=401)

    state = run_agent(PROJECT_DATA, nexla_client=client)

    assert state.finished is True
    assert state.evaluation["passed"] is True
    assert state.nexla_status["attempted"] is True
    assert state.nexla_status["connected"] is False
    assert state.nexla_status["used_for_timeline"] is False
    assert state.nexla_status["fallback_used"] is True
    assert state.nexla_status["error_type"] == "authentication_or_expired_token"
    assert {"calendar", "transactions", "emails"}.issubset(state.queried_sources)
    assert any(event.source == "transactions" for event in state.events)
    assert any("Nexla failed with authentication_or_expired_token" in entry.observation for entry in state.trace)


def test_status_ui_and_smoke_never_contain_token_or_payload() -> None:
    client, _ = _client()
    state = run_agent(PROJECT_DATA, nexla_client=client)
    app_source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    smoke_source = (PROJECT_ROOT / "scripts" / "nexla_smoke_test.py").read_text(
        encoding="utf-8"
    )

    assert TEST_TOKEN not in repr(state)
    assert "headers" not in repr(state.nexla_status)
    assert "response" not in repr(state.nexla_status)
    assert "Nexla role: Event normalization" in app_source
    assert "Samples received:" in app_source
    assert "Unique normalized events used:" in app_source
    assert "Remote timeline used: Yes" in app_source
    assert "Authorization" not in app_source
    assert "session_token" not in app_source
    assert "print(json.dumps(result" in smoke_source
    assert "response.json" not in smoke_source


@pytest.mark.parametrize(
    ("exception", "error_type"),
    [
        (
            httpx.ConnectTimeout(
                "safe fake timeout",
                request=httpx.Request("GET", "https://unit-test.invalid"),
            ),
            "connect_timeout",
        ),
        (
            httpx.ReadTimeout(
                "safe fake timeout",
                request=httpx.Request("GET", "https://unit-test.invalid"),
            ),
            "read_timeout",
        ),
        (
            httpx.ConnectError(
                "safe fake connection error",
                request=httpx.Request("GET", "https://unit-test.invalid"),
            ),
            "connect_error",
        ),
    ],
)
def test_httpx_errors_are_safely_classified(exception: Exception, error_type: str) -> None:
    client, _ = _client(error=exception)

    with pytest.raises(NexlaClientError) as caught:
        client.fetch_normalized_events()

    assert caught.value.error_type == error_type
    assert caught.value.diagnostics.exception_type == type(exception).__name__
    assert TEST_TOKEN not in str(caught.value)
