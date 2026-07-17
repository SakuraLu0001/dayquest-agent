"""Safe client for reading normalized DayQuest events from Nexla samples."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

from .models import Event
from .privacy import contains_forbidden_data


REQUIRED_EVENT_FIELDS = {
    "event_id",
    "start_time",
    "end_time",
    "event_type",
    "summary",
    "source",
    "confidence",
    "sensitivity",
    "redacted",
}
ALLOWED_SOURCES = {"calendar", "email_metadata", "developer_activity"}
ALLOWED_SENSITIVITY = {"low", "medium", "high"}
SAMPLE_ARRAY_KEYS = ("data", "records", "samples", "items")
RECORD_WRAPPER_KEYS = ("output", "data", "value")


@dataclass(frozen=True)
class NexlaConfig:
    api_host: str = ""
    session_token: str = ""
    nexset_id: str = ""
    timeout_seconds: float = 20.0


@dataclass(frozen=True)
class NexlaDiagnostics:
    http_status: int | None = None
    latency_ms: int | None = None
    exception_type: str = "None"
    cause_type: str = "None"
    context_type: str = "None"


@dataclass(frozen=True)
class NexlaSamplesResult:
    events: list[Event]
    nexset_id: str
    record_count: int
    raw_sample_count: int
    latency_ms: int
    http_status: int


class NexlaClientError(RuntimeError):
    """A categorized Nexla error that never contains response or credential data."""

    def __init__(
        self,
        error_type: str,
        diagnostics: NexlaDiagnostics | None = None,
    ) -> None:
        self.error_type = error_type
        self.diagnostics = diagnostics or NexlaDiagnostics()
        super().__init__(error_type)


def _parse_iso8601(value: Any, *, allow_empty: bool = False) -> str:
    if allow_empty and (value is None or value == ""):
        return ""
    if not isinstance(value, str) or not value.strip():
        raise NexlaClientError("invalid_schema")
    normalized = value.strip()
    try:
        datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        raise NexlaClientError("invalid_schema") from None
    return normalized


def normalized_record_to_event(record: Any) -> Event:
    """Validate one transformed record and retain only the normalized schema."""
    if not isinstance(record, dict) or not REQUIRED_EVENT_FIELDS.issubset(record):
        raise NexlaClientError("invalid_schema")

    record = {field: record[field] for field in REQUIRED_EVENT_FIELDS}

    event_id = record["event_id"]
    event_type = record["event_type"]
    summary = record["summary"]
    source = record["source"]
    sensitivity = record["sensitivity"]
    confidence = record["confidence"]
    redacted = record["redacted"]
    if not isinstance(event_id, str) or not event_id.strip():
        raise NexlaClientError("invalid_schema")
    if not isinstance(event_type, str) or not event_type.strip():
        raise NexlaClientError("invalid_schema")
    if not isinstance(summary, str) or not summary.strip() or contains_forbidden_data(summary):
        raise NexlaClientError("invalid_schema")
    if source not in ALLOWED_SOURCES or sensitivity not in ALLOWED_SENSITIVITY:
        raise NexlaClientError("invalid_schema")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise NexlaClientError("invalid_schema")
    if not 0 <= float(confidence) <= 1 or redacted is not True:
        raise NexlaClientError("invalid_schema")

    start_time = _parse_iso8601(record["start_time"])
    end_time = _parse_iso8601(record["end_time"], allow_empty=True) or start_time
    return Event(
        event_id=event_id.strip(),
        start_time=start_time,
        end_time=end_time,
        event_type=event_type.strip(),
        summary=summary.strip(),
        source=source,
        confidence=float(confidence),
        sensitivity=sensitivity,
        evidence={"status": "normalized event; Nexla metadata not retained"},
        redacted=True,
    )


def _locate_sample_records(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise NexlaClientError("invalid_schema")
    for key in SAMPLE_ARRAY_KEYS:
        candidate = payload.get(key)
        if isinstance(candidate, list):
            return candidate
    for outer_key in SAMPLE_ARRAY_KEYS:
        wrapper = payload.get(outer_key)
        if not isinstance(wrapper, dict):
            continue
        for inner_key in SAMPLE_ARRAY_KEYS:
            candidate = wrapper.get(inner_key)
            if isinstance(candidate, list):
                return candidate
    raise NexlaClientError("invalid_schema")


def _find_nested_records(value: Any, depth: int = 0) -> list[dict[str, Any]]:
    if depth > 5:
        return []
    if isinstance(value, dict):
        if REQUIRED_EVENT_FIELDS.issubset(value):
            return [value]
        records: list[dict[str, Any]] = []
        for nested_value in value.values():
            records.extend(_find_nested_records(nested_value, depth + 1))
        return records
    if isinstance(value, list):
        records: list[dict[str, Any]] = []
        for item in value:
            records.extend(_find_nested_records(item, depth + 1))
        return records
    return []


def _unwrap_sample_records(item: Any) -> list[dict[str, Any]]:
    if not isinstance(item, dict):
        raise NexlaClientError("invalid_schema")
    if REQUIRED_EVENT_FIELDS.issubset(item):
        return [item]
    for key in RECORD_WRAPPER_KEYS:
        if key not in item:
            continue
        records = _find_nested_records(item[key])
        if records:
            return records
    raise NexlaClientError("invalid_schema")


def _exception_diagnostics(exc: BaseException, latency_ms: int) -> NexlaDiagnostics:
    return NexlaDiagnostics(
        latency_ms=latency_ms,
        exception_type=type(exc).__name__,
        cause_type=type(exc.__cause__).__name__ if exc.__cause__ is not None else "None",
        context_type=(
            type(exc.__context__).__name__ if exc.__context__ is not None else "None"
        ),
    )


class NexlaClient:
    def __init__(self, config: NexlaConfig, client: Any | None = None) -> None:
        self.config = config
        self._client = client
        self.configuration_error = self._configuration_error()

    @classmethod
    def from_env(cls, env_path: str | Path | None = None) -> "NexlaClient":
        path = Path(env_path) if env_path else Path.cwd() / ".env"
        load_dotenv(dotenv_path=path, override=False)
        timeout_raw = os.getenv("NEXLA_TIMEOUT_SECONDS", "20")
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 0.0
        return cls(
            NexlaConfig(
                api_host=os.getenv("NEXLA_API_HOST", ""),
                session_token=os.getenv("NEXLA_SESSION_TOKEN", ""),
                nexset_id=os.getenv("NEXLA_NEXSET_ID", ""),
                timeout_seconds=timeout,
            )
        )

    @property
    def configured(self) -> bool:
        return self.configuration_error is None

    def _configuration_error(self) -> str | None:
        parsed = urlparse(self.config.api_host)
        if (
            not self.config.session_token
            or not self.config.nexset_id
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or self.config.timeout_seconds <= 0
        ):
            return "missing_config"
        return None

    def fetch_normalized_events(self) -> NexlaSamplesResult:
        if self.configuration_error:
            raise NexlaClientError("missing_config")
        endpoint = (
            f"{self.config.api_host.rstrip('/')}/data_sets/"
            f"{self.config.nexset_id}/samples"
        )
        headers = {
            "Authorization": f"Bearer {self.config.session_token}",
            "Accept": "application/vnd.nexla.api.v1+json",
        }
        try:
            client = self._client or httpx.Client(
                timeout=self.config.timeout_seconds,
                follow_redirects=False,
            )
        except Exception as exc:
            raise NexlaClientError(
                "connect_error",
                _exception_diagnostics(exc, 0),
            ) from None

        owns_client = self._client is None
        started = time.perf_counter()
        try:
            try:
                response = client.get(
                    endpoint,
                    headers=headers,
                    params={
                        "count": 20,
                        "include_metadata": "false",
                        "live": "false",
                    },
                    timeout=self.config.timeout_seconds,
                )
            except httpx.ConnectTimeout as exc:
                raise NexlaClientError(
                    "connect_timeout",
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None
            except httpx.ReadTimeout as exc:
                raise NexlaClientError(
                    "read_timeout",
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None
            except httpx.ConnectError as exc:
                raise NexlaClientError(
                    "connect_error",
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None
            except httpx.HTTPError as exc:
                raise NexlaClientError(
                    "connect_error",
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None
            except Exception as exc:
                raise NexlaClientError(
                    "connect_error",
                    _exception_diagnostics(exc, round((time.perf_counter() - started) * 1000)),
                ) from None

            latency_ms = round((time.perf_counter() - started) * 1000)
            diagnostics = NexlaDiagnostics(
                http_status=response.status_code,
                latency_ms=latency_ms,
            )
            status_error = {
                401: "authentication_or_expired_token",
                403: "forbidden",
                404: "nexset_not_found",
                429: "rate_limit",
            }.get(response.status_code)
            if status_error is None and response.status_code != 200:
                status_error = "connect_error"
            if status_error:
                raise NexlaClientError(status_error, diagnostics)

            try:
                payload = response.json()
            except ValueError:
                raise NexlaClientError("invalid_json", diagnostics) from None
            try:
                samples = _locate_sample_records(payload)
            except NexlaClientError as exc:
                raise NexlaClientError(exc.error_type, diagnostics) from None
            if not samples:
                raise NexlaClientError("empty_samples", diagnostics)
            try:
                normalized_records = [
                    record
                    for item in samples
                    for record in _unwrap_sample_records(item)
                ]
                events = [
                    normalized_record_to_event(record)
                    for record in normalized_records
                ]
            except NexlaClientError as exc:
                raise NexlaClientError(exc.error_type, diagnostics) from None
            return NexlaSamplesResult(
                events=events,
                nexset_id=self.config.nexset_id,
                record_count=len(events),
                raw_sample_count=len(samples),
                latency_ms=latency_ms,
                http_status=response.status_code,
            )
        finally:
            if owns_client:
                client.close()
