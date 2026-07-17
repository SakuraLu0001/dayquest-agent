from __future__ import annotations

from pathlib import Path

from dayquest.agent import run_agent
from dayquest.privacy import redact_text


PROJECT_DATA = Path(__file__).resolve().parents[1] / "data"


def test_email_is_removed() -> None:
    safe = redact_text("Write demo.user@example.com after the event.")
    assert "demo.user@example.com" not in safe
    assert "[REDACTED_EMAIL]" in safe


def test_exact_amount_is_generalized() -> None:
    safe = redact_text("Lunch cost $18.47.")
    assert "$18.47" not in safe
    assert "a small purchase" in safe


def test_address_is_generalized() -> None:
    safe = redact_text("Meet at 123 Market Street.")
    assert "123 Market Street" not in safe
    assert "near the venue" in safe


def test_final_scenes_have_no_email_amount_or_raw_email_body() -> None:
    state = run_agent(PROJECT_DATA)
    story = " ".join(
        f"{scene.title} {scene.fictional_event} {scene.narration} {scene.fictional_embellishment}"
        for scene in state.scenes
    )

    assert "@" not in story
    assert "$18.47" not in story
    assert "demo.user@example.com" not in story
    assert "arrive at Northbridge" not in story
    assert "Bring ideas, not credentials" not in story


def test_redacted_timeline_has_natural_transaction_summaries() -> None:
    state = run_agent(PROJECT_DATA)
    transaction_summaries = {
        event.event_type: event.summary
        for event in state.events
        if event.source == "transactions"
    }

    assert "near near" not in " ".join(transaction_summaries.values()).lower()
    assert transaction_summaries["coffee"] == (
        "Coffee at a local café for a small purchase near the venue."
    )
    assert transaction_summaries["travel"] == "Travel by local transit toward the event venue."
    assert "small purchase" not in transaction_summaries["travel"]
