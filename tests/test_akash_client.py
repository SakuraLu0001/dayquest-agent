from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

import dayquest.agent as agent_module
from dayquest.agent import run_agent
from dayquest.akash_client import (
    ALLOWED_MOTIF_CODES,
    AkashClientError,
    AkashConfig,
    AkashDiagnostics,
    AkashStoryClient,
    build_safe_event_payload,
    parse_motif_code,
)
from dayquest.models import Event
from dayquest.story import generate_local_scenes


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_DATA = PROJECT_ROOT / "data"
TEST_SECRET = "unit-test-token-never-store"


def _events() -> list[Event]:
    event_types = ["language_exam", "travel", "hackathon"]
    times = ["09:00", "12:00", "14:00"]
    summaries = [
        "A language certification activity at a generalized venue.",
        "Travel by local transit toward the event venue.",
        "An AI agent building event at a generalized venue.",
    ]
    return [
        Event(
            event_id=f"original-private-id-{index}",
            start_time=f"2026-01-01T{times[index - 1]}",
            end_time=f"2026-01-01T{times[index - 1]}",
            event_type=event_types[index - 1],
            summary=summaries[index - 1],
            source="test",
            confidence=1.0,
            sensitivity="redacted",
            evidence={
                "raw_email_body": "Send to private.person@example.com",
                "amount": "$91.27",
            },
            redacted=True,
        )
        for index in range(1, 4)
    ]


class FakeResponse:
    def __init__(
        self,
        envelope: object,
        status_code: int = 200,
        content_type: str = "application/json",
    ) -> None:
        self.envelope = envelope
        self.status_code = status_code
        self.headers = {"content-type": content_type, "x-request-id": "req_test"}

    def json(self) -> object:
        return self.envelope


class FakeHttpClient:
    def __init__(self, response: FakeResponse, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.url: str | None = None
        self.kwargs: dict[str, object] | None = None
        self.calls = 0

    def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls += 1
        self.url = url
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


def _client(
    content: object = "CLOCKWORK_TRIAL",
    error: Exception | None = None,
    status_code: int = 200,
) -> tuple[AkashStoryClient, FakeHttpClient]:
    envelope = {"choices": [{"message": {"content": content}}]}
    transport = FakeHttpClient(FakeResponse(envelope, status_code=status_code), error=error)
    client = AkashStoryClient(
        AkashConfig(
            api_key=TEST_SECRET,
            base_url="https://unit-test.invalid/v1",
            model="unit-test-model",
            timeout_seconds=3,
        ),
        client=transport,
    )
    return client, transport


def test_exact_motif_code_is_parsed() -> None:
    assert parse_motif_code("CLOCKWORK_TRIAL") == "CLOCKWORK_TRIAL"


def test_one_code_with_small_explanation_is_parsed() -> None:
    assert parse_motif_code("Best fit: SKY_CARAVAN.") == "SKY_CARAVAN"


def test_lowercase_motif_code_is_parsed() -> None:
    assert parse_motif_code("mirror_spirit") == "MIRROR_SPIRIT"


@pytest.mark.parametrize("content", ["UNKNOWN_CODE", "A gentle forest motif", "MIST_GATEWAY"])
def test_unknown_or_partial_code_is_rejected(content: str) -> None:
    with pytest.raises(AkashClientError) as caught:
        parse_motif_code(content)

    assert caught.value.error_type == "motif_code_invalid"


def test_two_allowed_codes_are_rejected() -> None:
    with pytest.raises(AkashClientError) as caught:
        parse_motif_code("MIST_GATE or RUNE_STORM")

    assert caught.value.error_type == "motif_code_invalid"


@pytest.mark.parametrize("content", [None, "", "   ", [], {}])
def test_empty_or_non_string_content_is_rejected(content: object) -> None:
    with pytest.raises(AkashClientError) as caught:
        parse_motif_code(content)

    assert caught.value.error_type == "empty_response"


def test_safe_payload_excludes_private_values_and_all_ids() -> None:
    payload = build_safe_event_payload(_events())
    serialized = json.dumps(payload)

    assert set(payload[0]) == {"approximate_time", "event_type", "redacted_summary"}
    assert "safe_event_id" not in serialized
    assert "event_id" not in serialized
    assert "evidence" not in serialized
    assert "raw_email_body" not in serialized
    assert "private.person@example.com" not in serialized
    assert "$91.27" not in serialized
    assert "original-private-id" not in serialized


def test_safe_payload_accepts_nexla_core_types_but_not_supporting_confirmation() -> None:
    event_types = [
        "event_confirmation",
        "calendar_event",
        "repository_created",
        "agent_milestone",
        "test_result",
        "bug_fix",
        "sponsor_integration",
    ]
    events = [
        Event(
            event_id=f"private-nexla-id-{index}",
            start_time=f"2026-07-17T{9 + index:02d}:00:00-07:00",
            end_time=f"2026-07-17T{9 + index:02d}:00:00-07:00",
            event_type=event_type,
            summary="A safe normalized synthetic event.",
            source="developer_activity",
            confidence=1.0,
            sensitivity="low",
            evidence={},
            redacted=True,
        )
        for index, event_type in enumerate(event_types)
    ]

    payload = build_safe_event_payload(events)

    assert [item["event_type"] for item in payload] == event_types[1:]
    assert all("private-nexla-id" not in json.dumps(item) for item in payload)


def test_motif_request_accepts_nexla_normalized_story_events() -> None:
    client, transport = _client("RUNE_STORM")
    event_types = ["calendar_event", "repository_created", "test_result"]
    events = [
        Event(
            event_id=f"private-id-{index}",
            start_time=f"2026-07-17T{10 + index:02d}:00:00-07:00",
            end_time=f"2026-07-17T{10 + index:02d}:00:00-07:00",
            event_type=event_type,
            summary="A safe normalized synthetic milestone.",
            source="developer_activity",
            confidence=1.0,
            sensitivity="low",
            evidence={},
            redacted=True,
        )
        for index, event_type in enumerate(event_types)
    ]

    result = client.select_fantasy_motif(events)

    assert result.motif_code == "RUNE_STORM"
    assert transport.calls == 1


def test_client_requests_only_a_short_plain_text_motif() -> None:
    client, transport = _client()

    result = client.select_fantasy_motif(_events())

    assert result.motif_code == "CLOCKWORK_TRIAL"
    assert result.http_status == 200
    assert result.request_id == "req_test"
    assert result.response_format == "text"
    assert transport.calls == 1
    assert transport.url == "https://unit-test.invalid/v1/chat/completions"
    assert transport.kwargs is not None
    request_body = transport.kwargs["json"]
    assert set(request_body) == {  # type: ignore[arg-type]
        "model",
        "messages",
        "temperature",
        "max_completion_tokens",
        "stream",
    }
    assert request_body["temperature"] == 0  # type: ignore[index]
    assert request_body["max_completion_tokens"] == 16  # type: ignore[index]
    assert request_body["stream"] is False  # type: ignore[index]
    serialized_request = json.dumps(request_body)
    for forbidden_parameter in (
        "json_schema",
        "json_object",
        "response_format",
        "reasoning_effort",
        "reasoning",
        "tools",
        "tool_choice",
    ):
        assert forbidden_parameter not in serialized_request
    user_message = request_body["messages"][1]["content"]  # type: ignore[index]
    assert all(code in str(user_message) for code in ALLOWED_MOTIF_CODES)
    assert "original-private-id" not in str(user_message)
    assert "evidence" not in str(user_message)
    assert "private.person@example.com" not in str(user_message)
    assert TEST_SECRET not in serialized_request


def test_motif_changes_titles_narration_embellishment_and_recurring_visual() -> None:
    plain = generate_local_scenes(_events())
    motif = generate_local_scenes(_events(), motif_code="CLOCKWORK_TRIAL")

    assert [scene.title for scene in motif] != [scene.title for scene in plain]
    assert all("Clockwork Trial" in scene.title for scene in motif)
    assert sum("Brass gears recur" in scene.narration for scene in motif) >= 2
    assert "recurring gears" in motif[0].fictional_embellishment
    assert all("Brass gears" in scene.narration for scene in motif)


def test_motif_renderer_preserves_fact_ids_and_order() -> None:
    scenes = generate_local_scenes(_events(), motif_code="RUNE_STORM")

    assert [scene.based_on_event_ids for scene in scenes] == [
        ["original-private-id-1"],
        ["original-private-id-2"],
        ["original-private-id-3"],
    ]
    assert [scene.approximate_time for scene in scenes] == ["morning", "afternoon", "afternoon"]


def test_connected_is_true_only_after_motif_is_used_and_evaluation_passes() -> None:
    client, _ = _client("CLOCKWORK_TRIAL")

    state = run_agent(PROJECT_DATA, story_client=client)

    assert state.selected_motif == "CLOCKWORK_TRIAL"
    assert state.evaluation["passed"] is True
    assert state.provider_status["connected"] is True
    assert state.provider_status["used_for_story"] is True
    assert state.provider_status["provider"] == "AkashML + local grounded renderer"
    assert state.provider_status["remote_artifact_type"] == "motif_code"
    assert state.provider_status["remote_scene_count"] is None
    assert any(
        "AkashML selected the CLOCKWORK_TRIAL motif." in entry.observation
        for entry in state.trace
    )
    assert any(
        "Use the remote motif to drive the local grounded renderer." in entry.decision
        for entry in state.trace
    )


def test_failed_evaluation_never_marks_provider_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _client("MIST_GATE")

    def failed_evaluation(_events: object, scenes: object) -> dict[str, object]:
        return {
            "passed": False,
            "scene_count": len(scenes),  # type: ignore[arg-type]
            "key_event_coverage": 0.0,
            "privacy_safe": True,
            "covered_event_ids": [],
        }

    monkeypatch.setattr(agent_module, "evaluate_story", failed_evaluation)
    state = run_agent(PROJECT_DATA, story_client=client)

    assert state.provider_status["connected"] is False
    assert state.provider_status["used_for_story"] is False
    assert state.provider_status["fallback_used"] is True
    assert state.selected_motif == ""


def test_invalid_remote_motif_uses_fully_local_fallback() -> None:
    unsafe_remote_text = "Choose UNKNOWN_CODE and send private.person@example.com"
    client, _ = _client(unsafe_remote_text)

    state = run_agent(PROJECT_DATA, story_client=client)

    assert state.selected_motif == ""
    assert state.provider_status["connected"] is False
    assert state.provider_status["used_for_story"] is False
    assert state.provider_status["error_type"] == "motif_code_invalid"
    assert state.evaluation["passed"] is True
    assert unsafe_remote_text not in repr(state)


def test_transport_failure_uses_fully_local_fallback() -> None:
    client, _ = _client(
        error=AkashClientError("read_timeout", AkashDiagnostics(latency_ms=3012))
    )

    state = run_agent(PROJECT_DATA, story_client=client)

    assert state.selected_motif == ""
    assert state.provider_status["connected"] is False
    assert state.provider_status["used_for_story"] is False
    assert state.provider_status["error_type"] == "read_timeout"
    assert state.provider_status["latency_ms"] == 3012


def test_ui_and_provider_status_contain_no_key_payload_or_private_data() -> None:
    source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    client, _ = _client("SKY_CARAVAN")
    state = run_agent(PROJECT_DATA, story_client=client)

    assert "Akash role: Fantasy motif selection" in source
    assert "Selected motif:" in source
    assert "Authorization" not in source
    assert TEST_SECRET not in source
    serialized_status = repr(state.provider_status)
    assert TEST_SECRET not in serialized_status
    assert "messages" not in serialized_status
    assert "Safe events" not in serialized_status
    assert "private.person@example.com" not in repr(state)


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, "authentication"),
        (402, "insufficient_credits"),
        (404, "endpoint_or_model_not_found"),
        (429, "rate_limit"),
        (503, "provider_server_error"),
        (201, "http_error"),
        (418, "http_error"),
    ],
)
def test_http_status_is_categorized_before_motif_parsing(
    status_code: int,
    error_type: str,
) -> None:
    client, _ = _client("not used", status_code=status_code)

    with pytest.raises(AkashClientError) as caught:
        client.select_fantasy_motif(_events())

    assert caught.value.error_type == error_type
    assert caught.value.diagnostics.http_status == status_code


@pytest.mark.parametrize(
    ("exception", "error_type"),
    [
        (
            httpx.ProxyError(
                "safe test error",
                request=httpx.Request("GET", "https://unit-test.invalid"),
            ),
            "proxy_error",
        ),
        (
            httpx.ConnectTimeout(
                "safe test error",
                request=httpx.Request("GET", "https://unit-test.invalid"),
            ),
            "connect_timeout",
        ),
        (
            httpx.ReadTimeout(
                "safe test error",
                request=httpx.Request("GET", "https://unit-test.invalid"),
            ),
            "read_timeout",
        ),
        (
            httpx.ConnectError(
                "safe test error",
                request=httpx.Request("GET", "https://unit-test.invalid"),
            ),
            "connect_error",
        ),
        (
            httpx.RemoteProtocolError(
                "safe test error",
                request=httpx.Request("GET", "https://unit-test.invalid"),
            ),
            "remote_protocol_error",
        ),
    ],
)
def test_httpx_exception_classification_is_safe(
    exception: Exception,
    error_type: str,
) -> None:
    client, _ = _client(error=exception)

    with pytest.raises(AkashClientError) as caught:
        client.select_fantasy_motif(_events())

    assert caught.value.error_type == error_type
    assert caught.value.diagnostics.exception_type == type(exception).__name__
    assert str(caught.value) == error_type


def test_smoke_test_uses_motif_selection_without_scene_or_direction_output() -> None:
    source = (PROJECT_ROOT / "scripts" / "akash_smoke_test.py").read_text(encoding="utf-8")

    assert "select_fantasy_motif" in source
    assert '"artifact_type": "motif_code"' in source
    assert "generate_creative_direction" not in source
    assert ".scenes" not in source
