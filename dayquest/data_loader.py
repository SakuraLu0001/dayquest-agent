"""Strict local loaders for DayQuest's synthetic sources."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .models import Event


class DataLoadError(ValueError):
    """A source-specific error suitable for display in the UI."""

    def __init__(self, path: Path, problem: str, check: str) -> None:
        self.path = path
        self.problem = problem
        self.check = check
        super().__init__(f"{path}: {problem} Check {check}.")


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise DataLoadError(path, "file is missing", "that the file exists in data/")
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise DataLoadError(
            path,
            f"invalid JSON near line {exc.lineno}, column {exc.colno}",
            "commas, quotes, and brackets",
        ) from exc


def _require(record: dict[str, Any], fields: set[str], path: Path) -> None:
    missing = sorted(fields - record.keys())
    if missing:
        raise DataLoadError(
            path,
            f"required fields are missing: {', '.join(missing)}",
            "the source schema documented in the sample data",
        )


def _ending_at(start: str, minutes: int = 20) -> str:
    try:
        parsed = datetime.fromisoformat(start)
    except ValueError as exc:
        raise ValueError(f"invalid ISO timestamp: {start}") from exc
    return (parsed + timedelta(minutes=minutes)).isoformat(timespec="minutes")


def load_calendar(data_dir: Path) -> list[Event]:
    path = data_dir / "calendar.json"
    payload = _read_json(path)
    records = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise DataLoadError(path, "top-level 'events' must be a list", "the JSON structure")

    events: list[Event] = []
    required = {"event_id", "start_time", "end_time", "event_type", "summary", "location"}
    for record in records:
        if not isinstance(record, dict):
            raise DataLoadError(path, "each event must be an object", "every events[] entry")
        _require(record, required, path)
        events.append(
            Event(
                event_id=str(record["event_id"]),
                start_time=str(record["start_time"]),
                end_time=str(record["end_time"]),
                event_type=str(record["event_type"]),
                summary=f"{record['summary']} at {record['location']}",
                source="calendar",
                confidence=0.92,
                sensitivity="unreviewed",
                evidence=dict(record),
            )
        )
    return events


def load_transactions(data_dir: Path) -> list[Event]:
    path = data_dir / "transactions.csv"
    if not path.exists():
        raise DataLoadError(path, "file is missing", "that the file exists in data/")
    required = {"transaction_id", "timestamp", "merchant", "amount", "category", "location"}
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or [])
            missing = sorted(required - fields)
            if missing:
                raise DataLoadError(
                    path,
                    f"CSV columns are missing: {', '.join(missing)}",
                    "the header row",
                )
            rows = list(reader)
    except UnicodeDecodeError as exc:
        raise DataLoadError(path, "file is not valid UTF-8", "the CSV encoding") from exc

    events: list[Event] = []
    for row in rows:
        try:
            float(row["amount"])
            end_time = _ending_at(row["timestamp"])
        except (TypeError, ValueError) as exc:
            raise DataLoadError(path, str(exc), "transaction timestamps and amounts") from exc
        if row["category"] == "travel":
            summary = f"Travel by {row['merchant']} toward the event venue."
        else:
            summary = (
                f"{row['category'].title()} at {row['merchant']} "
                f"for ${float(row['amount']):.2f} {row['location']}."
            )
        events.append(
            Event(
                event_id=f"txn-{row['transaction_id']}",
                start_time=row["timestamp"],
                end_time=end_time,
                event_type=row["category"],
                summary=summary,
                source="transactions",
                confidence=0.78,
                sensitivity="unreviewed",
                evidence=dict(row),
            )
        )
    return events


def load_emails(data_dir: Path) -> list[Event]:
    path = data_dir / "emails.json"
    payload = _read_json(path)
    records = payload.get("emails") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise DataLoadError(path, "top-level 'emails' must be a list", "the JSON structure")

    required = {"email_id", "sent_at", "sender", "subject", "body"}
    events: list[Event] = []
    for record in records:
        if not isinstance(record, dict):
            raise DataLoadError(path, "each email must be an object", "every emails[] entry")
        _require(record, required, path)
        subject = str(record["subject"])
        lowered = subject.lower()
        if "exam" in lowered or "certification" in lowered:
            event_type = "exam_confirmation"
        elif "hackathon" in lowered or "forge" in lowered:
            event_type = "hackathon_confirmation"
        else:
            event_type = "email"
        try:
            end_time = _ending_at(str(record["sent_at"]), 5)
        except ValueError as exc:
            raise DataLoadError(path, str(exc), "email timestamps") from exc
        events.append(
            Event(
                event_id=str(record["email_id"]),
                start_time=str(record["sent_at"]),
                end_time=end_time,
                event_type=event_type,
                summary=f"Email: {subject} — {record['body']}",
                source="emails",
                confidence=0.84,
                sensitivity="unreviewed",
                evidence=dict(record),
            )
        )
    return events
