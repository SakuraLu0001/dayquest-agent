from __future__ import annotations

import json
from pathlib import Path

from dayquest.agent import run_agent


PROJECT_DATA = Path(__file__).resolve().parents[1] / "data"


def test_agent_completes_with_bounded_observation_driven_loop() -> None:
    state = run_agent(PROJECT_DATA)

    assert state.finished is True
    assert state.iteration <= 5
    assert state.stop_reason
    assert len(state.scenes) >= 3
    assert state.evaluation["passed"] is True
    assert all(
        entry.action and entry.observation and entry.decision and entry.reason
        for entry in state.trace
    )


def test_transaction_observation_changes_the_following_action() -> None:
    state = run_agent(PROJECT_DATA)
    transaction_index = next(
        index for index, entry in enumerate(state.trace) if entry.action == "READ_TRANSACTIONS"
    )
    transaction_entry = state.trace[transaction_index]
    following_entry = state.trace[transaction_index + 1]

    assert "purchase/travel clues" in transaction_entry.observation
    assert following_entry.action == "READ_EMAILS"
    assert "purchase/travel clues" in following_entry.reason


def test_agent_is_not_an_unconditional_fixed_pipeline(tmp_path: Path) -> None:
    calendar = {
        "events": [
            {
                "event_id": "all-day-exam",
                "start_time": "2026-07-17T08:00",
                "end_time": "2026-07-17T20:00",
                "event_type": "language_exam",
                "summary": "Synthetic language exam",
                "location": "Northbridge Language Center",
            }
        ]
    }
    emails = {
        "emails": [
            {
                "email_id": "mail-one",
                "sent_at": "2026-07-17T07:00",
                "sender": "demo@example.invalid",
                "subject": "Exam reminder",
                "body": "Synthetic reminder only.",
            }
        ]
    }
    (tmp_path / "calendar.json").write_text(json.dumps(calendar), encoding="utf-8")
    (tmp_path / "emails.json").write_text(json.dumps(emails), encoding="utf-8")

    state = run_agent(tmp_path)
    actions = [entry.action for entry in state.trace]

    assert actions[0] == "READ_CALENDAR"
    assert actions[1] == "READ_EMAILS"
    assert "READ_TRANSACTIONS" not in actions
    assert state.finished is True
    assert "fewer than three" in state.stop_reason


def test_missing_source_is_reported_without_blank_run(tmp_path: Path) -> None:
    state = run_agent(tmp_path)

    assert state.finished is True
    assert state.errors
    assert any("calendar.json" in error for error in state.errors)
    assert state.trace
    assert state.stop_reason

