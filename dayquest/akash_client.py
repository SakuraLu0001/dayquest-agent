"""Privacy-safe AkashML client for selecting one fantasy motif code."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

from .models import Event
from .privacy import contains_forbidden_data


STORY_EVENT_TYPES = {
    "language_exam",
    "coffee",
    "lunch",
    "travel",
    "hackathon",
    "calendar_event",
    "repository_created",
    "agent_milestone",
    "test_result",
    "bug_fix",
    "sponsor_integration",
}
ALLOWED_MOTIF_CODES = (
    "MIST_GATE",
    "CLOCKWORK_TRIAL",
    "RUNE_STORM",
    "SKY_CARAVAN",
    "MIRROR_SPIRIT",
)


@dataclass(frozen=True)
class AkashConfig:
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class AkashMotifResult:
    motif_code: str
    model: str
    http_status: int
    latency_ms: int
    request_id: str | None
    response_format: str = "text"


@dataclass(frozen=True)
class AkashDiagnostics:
    http_status: int | None = None
    content_type: str = "unknown"
    top_level_keys: tuple[str, ...] = ()
    choices_count: int | None = None
    message_content_type: str = "unknown"
    latency_ms: int | None = None
    exception_type: str = "None"
    cause_type: str = "None"
    context_type: str = "None"
    content_length: int = 0
    response_format: str = "text"
    remote_scene_count: int | None = None


class AkashClientError(RuntimeError):
    """A categorized error that deliberately excludes provider response details."""

    def __init__(
        self,
        error_type: str,
        diagnostics: AkashDiagnostics | None = None,
    ) -> None:
        self.error_type = error_type
        self.diagnostics = diagnostics or AkashDiagnostics()
        super().__init__(error_type)


def _time_bucket(iso_time: str) -> str:
    try:
        hour = int(iso_time[11:13])
    except (TypeError, ValueError, IndexError) as exc:
        raise AkashClientError("schema_validation") from exc
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def build_safe_event_payload(events: list[Event]) -> list[dict[str, str]]:
    """Create the minimal anonymous event representation permitted to leave locally."""
    payload: list[dict[str, str]] = []
    candidates = sorted(
        (event for event in events if event.event_type in STORY_EVENT_TYPES),
        key=lambda event: event.start_time,
    )
    for event in candidates:
        if contains_forbidden_data(event.summary):
            raise AkashClientError("privacy_validation")
        payload.append(
            {
                "approximate_time": _time_bucket(event.start_time),
                "event_type": event.event_type,
                "redacted_summary": event.summary,
            }
        )
    if len(payload) < 3:
        raise AkashClientError("schema_validation")
    outbound_text = "\n".join(
        f"{item['approximate_time']} | {item['event_type']} | {item['redacted_summary']}"
        for item in payload
    )
    if contains_forbidden_data(outbound_text):
        raise AkashClientError("privacy_validation")
    return payload


def parse_motif_code(content: Any) -> str:
    """Extract exactly one allowed motif without preserving invalid model text."""
    if not isinstance(content, str) or not content.strip():
        raise AkashClientError("empty_response")
    normalized = content.strip().upper()
    matches = {
        code
        for code in ALLOWED_MOTIF_CODES
        if re.search(rf"(?<![A-Z0-9_]){re.escape(code)}(?![A-Z0-9_])", normalized)
    }
    if len(matches) != 1:
        raise AkashClientError("motif_code_invalid")
    return matches.pop()


def _safe_request_id(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value[:128] if re.fullmatch(r"[A-Za-z0-9_.:-]+", value[:128]) else None


def _content_type(response: httpx.Response | Any) -> str:
    value = response.headers.get("content-type", "unknown")
    return value.split(";", 1)[0].strip().lower() or "unknown"


def _top_level_keys(value: Any) -> tuple[str, ...]:
    if not isinstance(value, dict):
        return ()
    return tuple(sorted(str(key)[:64] for key in value.keys()))


def _diagnostics(
    *,
    response: httpx.Response | Any | None = None,
    envelope: Any = None,
    message_content: Any = None,
    latency_ms: int | None = None,
) -> AkashDiagnostics:
    choices = envelope.get("choices") if isinstance(envelope, dict) else None
    return AkashDiagnostics(
        http_status=getattr(response, "status_code", None),
        content_type=_content_type(response) if response is not None else "unknown",
        top_level_keys=_top_level_keys(envelope),
        choices_count=len(choices) if isinstance(choices, list) else None,
        message_content_type=(
            type(message_content).__name__ if message_content is not None else "unknown"
        ),
        latency_ms=latency_ms,
        content_length=len(message_content) if isinstance(message_content, str) else 0,
    )


def _exception_diagnostics(exc: BaseException, latency_ms: int) -> AkashDiagnostics:
    return AkashDiagnostics(
        latency_ms=latency_ms,
        exception_type=type(exc).__name__,
        cause_type=type(exc.__cause__).__name__ if exc.__cause__ is not None else "None",
        context_type=(
            type(exc.__context__).__name__ if exc.__context__ is not None else "None"
        ),
    )


class AkashStoryClient:
    def __init__(self, config: AkashConfig, client: Any | None = None) -> None:
        self.config = config
        self._client = client
        self.configuration_error = self._configuration_error()

    @classmethod
    def from_env(cls, env_path: str | Path | None = None) -> "AkashStoryClient":
        path = Path(env_path) if env_path else Path.cwd() / ".env"
        load_dotenv(dotenv_path=path, override=False)
        timeout_raw = os.getenv("AKASH_TIMEOUT_SECONDS", "30")
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 0.0
        return cls(
            AkashConfig(
                api_key=os.getenv("AKASH_API_KEY", ""),
                base_url=os.getenv("AKASH_BASE_URL", ""),
                model=os.getenv("AKASH_MODEL", ""),
                timeout_seconds=timeout,
            )
        )

    @property
    def configured(self) -> bool:
        return self.configuration_error is None

    def _configuration_error(self) -> str | None:
        if not self.config.api_key:
            return "missing_api_key"
        try:
            self.config.api_key.encode("ascii")
        except UnicodeEncodeError:
            return "invalid_api_key_encoding"
        if any(character.isspace() for character in self.config.api_key):
            return "invalid_api_key_format"
        if not self.config.base_url:
            return "missing_base_url"
        parsed = urlparse(self.config.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return "invalid_base_url"
        if not self.config.model:
            return "missing_model"
        if self.config.timeout_seconds <= 0:
            return "invalid_timeout"
        return None

    def select_fantasy_motif(
        self,
        events: list[Event],
        max_completion_tokens: int = 16,
    ) -> AkashMotifResult:
        if self.configuration_error:
            raise AkashClientError(self.configuration_error)
        safe_events = build_safe_event_payload(events)
        allowed_codes = "\n".join(ALLOWED_MOTIF_CODES)
        event_lines = "\n".join(
            f"- {item['approximate_time']} | {item['event_type']} | {item['redacted_summary']}"
            for item in safe_events
        )
        system_prompt = (
            "You select one safe high-fantasy motif for a grounded daily story. "
            "Return exactly one code from the allowed list. Do not explain your answer. "
            "Do not return Markdown."
        )
        user_prompt = f"Allowed codes:\n{allowed_codes}\n\nSafe events:\n{event_lines}"
        request_body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_completion_tokens": max_completion_tokens,
            "stream": False,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        endpoint = f"{self.config.base_url.rstrip('/')}/chat/completions"
        try:
            client = self._client or httpx.Client(
                timeout=self.config.timeout_seconds,
                follow_redirects=False,
            )
        except Exception as exc:
            raise AkashClientError("http_client_error", _exception_diagnostics(exc, 0)) from None

        owns_client = self._client is None
        started = time.perf_counter()
        try:
            try:
                response = client.post(
                    endpoint,
                    headers=headers,
                    json=request_body,
                    timeout=self.config.timeout_seconds,
                )
            except AkashClientError:
                raise
            except UnicodeEncodeError as exc:
                error_type = "invalid_header_encoding"
                raise AkashClientError(
                    error_type,
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None
            except httpx.ProxyError as exc:
                error_type = "proxy_error"
                raise AkashClientError(
                    error_type,
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None
            except httpx.ConnectTimeout as exc:
                error_type = "connect_timeout"
                raise AkashClientError(
                    error_type,
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None
            except httpx.ReadTimeout as exc:
                error_type = "read_timeout"
                raise AkashClientError(
                    error_type,
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None
            except httpx.ConnectError as exc:
                error_type = "connect_error"
                raise AkashClientError(
                    error_type,
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None
            except httpx.RemoteProtocolError as exc:
                error_type = "remote_protocol_error"
                raise AkashClientError(
                    error_type,
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None
            except httpx.HTTPError as exc:
                error_type = "http_client_error"
                raise AkashClientError(
                    error_type,
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None
            except Exception as exc:
                raise AkashClientError(
                    "unexpected_error",
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None

            latency_ms = round((time.perf_counter() - started) * 1000)
            try:
                envelope = response.json()
            except ValueError:
                envelope = None

            status_error = {
                401: "authentication",
                402: "insufficient_credits",
                404: "endpoint_or_model_not_found",
                429: "rate_limit",
            }.get(response.status_code)
            if status_error is None and 500 <= response.status_code <= 599:
                status_error = "provider_server_error"
            if status_error is None and response.status_code != 200:
                status_error = "http_error"
            if status_error is not None:
                raise AkashClientError(
                    status_error,
                    _diagnostics(response=response, envelope=envelope, latency_ms=latency_ms),
                )
            if envelope is None:
                raise AkashClientError(
                    "response_json_invalid",
                    _diagnostics(response=response, latency_ms=latency_ms),
                )

            base_diagnostics = _diagnostics(
                response=response,
                envelope=envelope,
                latency_ms=latency_ms,
            )
            if not isinstance(envelope, dict):
                raise AkashClientError("response_schema", base_diagnostics)
            choices = envelope.get("choices")
            if not isinstance(choices, list) or not choices:
                raise AkashClientError("response_schema", base_diagnostics)
            first_choice = choices[0]
            if not isinstance(first_choice, dict) or not isinstance(
                first_choice.get("message"), dict
            ):
                raise AkashClientError("response_schema", base_diagnostics)
            message_content = first_choice["message"].get("content")
            content_diagnostics = _diagnostics(
                response=response,
                envelope=envelope,
                message_content=message_content,
                latency_ms=latency_ms,
            )
            try:
                motif_code = parse_motif_code(message_content)
            except AkashClientError as exc:
                raise AkashClientError(exc.error_type, content_diagnostics) from None
            return AkashMotifResult(
                motif_code=motif_code,
                model=self.config.model,
                http_status=response.status_code,
                latency_ms=latency_ms,
                request_id=_safe_request_id(response.headers.get("x-request-id")),
            )
        finally:
            if owns_client:
                client.close()
