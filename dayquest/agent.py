"""Observation-driven local agent loop for DayQuest."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .data_loader import DataLoadError, load_calendar, load_emails, load_transactions
from .models import Action, AgentState, Event, TraceEntry
from .privacy import redact_events
from .story import evaluate_story, generate_story


LOADERS = {
    Action.READ_CALENDAR: ("calendar", load_calendar),
    Action.READ_TRANSACTIONS: ("transactions", load_transactions),
    Action.READ_EMAILS: ("emails", load_emails),
}


def _hour(iso_time: str) -> datetime:
    return datetime.fromisoformat(iso_time)


def analyze_gaps(events: list[Event]) -> list[str]:
    """Find meaningful gaps within the active 08:00–20:00 window."""
    if not events:
        return ["08:00–20:00 (no reconstructed events)"]
    intervals = sorted((_hour(event.start_time), _hour(event.end_time)) for event in events)
    day = intervals[0][0].date()
    cursor = datetime.combine(day, datetime.min.time()).replace(hour=8)
    end_of_day = cursor.replace(hour=20)
    gaps: list[str] = []
    for start, end in intervals:
        if end < cursor or start > end_of_day:
            continue
        if start > cursor and (start - cursor).total_seconds() >= 45 * 60:
            gaps.append(f"{cursor:%H:%M}–{start:%H:%M}")
        cursor = max(cursor, end)
    if end_of_day > cursor and (end_of_day - cursor).total_seconds() >= 45 * 60:
        gaps.append(f"{cursor:%H:%M}–{end_of_day:%H:%M}")
    return gaps


def _key_event_count(events: list[Event]) -> int:
    return sum(
        event.event_type in {"language_exam", "coffee", "lunch", "travel", "hackathon"}
        for event in events
    )


def _decide(state: AgentState, last_observation: str) -> tuple[list[Action], str]:
    if "calendar" not in state.queried_sources:
        return [Action.READ_CALENDAR], "No events exist yet, so the calendar is the least-sensitive starting source."

    if "transactions" not in state.queried_sources and state.missing_time_ranges:
        return [Action.READ_TRANSACTIONS], (
            "The previous observation exposed substantial timeline gaps; small transaction clues may explain travel or a meal."
        )

    transaction_clues = any(
        event.source == "transactions" and event.event_type in {"coffee", "lunch", "travel"}
        for event in state.events
    )
    if "emails" not in state.queried_sources and (transaction_clues or _key_event_count(state.events) < 3):
        clue = "purchase/travel clues now need confirmation" if transaction_clues else "too few key events were recovered"
        return [Action.READ_EMAILS], f"The previous observation indicates {clue}, so confirmation mail is the next useful source."

    if not state.scenes and not state.finished:
        return [Action.ANALYZE_TIMELINE, Action.REDACT_PRIVATE_DATA, Action.GENERATE_STORY], (
            "The collected observations now contain enough cross-source evidence; analysis and the privacy gate must precede storytelling."
        )

    if state.scenes and not state.evaluation:
        return [Action.EVALUATE_STORY, Action.STOP], (
            "A candidate story exists, so coverage and privacy must be evaluated before the loop can stop."
        )

    return [Action.STOP], f"No additional action can improve the state after: {last_observation}"


def _load(action: Action, state: AgentState, data_dir: Path) -> str:
    source, loader = LOADERS[action]
    state.queried_sources.append(source)
    try:
        loaded = loader(data_dir)
    except DataLoadError as exc:
        message = f"{exc.path.name}: {exc.problem}. Check {exc.check}."
        state.errors.append(message)
        if source == "calendar":
            state.missing_time_ranges = ["08:00–20:00 (calendar unavailable)"]
        return f"{source} could not be read: {message} Other sources remain available."

    state.events.extend(loaded)
    if source == "calendar":
        state.missing_time_ranges = analyze_gaps(state.events)
        return (
            f"Loaded {len(loaded)} calendar events and observed {len(state.missing_time_ranges)} large timeline gaps: "
            f"{', '.join(state.missing_time_ranges) or 'none'}."
        )
    if source == "transactions":
        clues = sorted({event.event_type for event in loaded})
        return f"Loaded {len(loaded)} transaction clues ({', '.join(clues)}); purchase/travel clues can guide confirmation lookup."
    signals = sorted({event.event_type for event in loaded})
    return f"Loaded {len(loaded)} email confirmation signals ({', '.join(signals)}), without exposing bodies to the story generator."


def _execute(actions: list[Action], state: AgentState, data_dir: Path) -> tuple[str, str]:
    if len(actions) == 1 and actions[0] in LOADERS:
        observation = _load(actions[0], state, data_dir)
        return observation, "Use this observation to choose the next unqueried source or begin safe synthesis."

    if Action.ANALYZE_TIMELINE in actions:
        state.events.sort(key=lambda event: event.start_time)
        state.missing_time_ranges = analyze_gaps(state.events)
        state.events, state.privacy_risks = redact_events(state.events)
        state.scenes = generate_story(state.events)
        if not state.scenes:
            state.finished = True
            state.stop_reason = "Stopped safely: fewer than three key events were available for a faithful story."
            return (
                f"Analyzed {len(state.events)} events and applied the privacy gate, but fewer than 3 story scenes were supportable.",
                "STOP without inventing unsupported events.",
            )
        return (
            f"Analyzed {len(state.events)} events, found {len(state.missing_time_ranges)} gaps, "
            f"handled {len(state.privacy_risks['Detected'])} privacy risks, and generated {len(state.scenes)} scenes.",
            "Evaluate event coverage and scan the complete story for residual private data.",
        )

    if Action.EVALUATE_STORY in actions:
        state.evaluation = evaluate_story(state.events, state.scenes)
        if not state.evaluation["passed"]:
            state.scenes = generate_story(state.events, revision=True)
            state.evaluation = evaluate_story(state.events, state.scenes)
            state.evaluation["revised_once"] = True
        state.finished = True
        if state.evaluation["passed"]:
            state.stop_reason = "Success: key events are covered, the story is privacy-safe, and the evaluation passed."
        else:
            state.stop_reason = "Stopped after one revision: story evaluation did not meet all safety and coverage thresholds."
        return (
            f"Evaluation passed={state.evaluation['passed']}, coverage={state.evaluation['key_event_coverage']}, "
            f"privacy_safe={state.evaluation['privacy_safe']}.",
            f"STOP — {state.stop_reason}",
        )

    state.finished = True
    state.stop_reason = state.stop_reason or "Stopped because no useful next action remained."
    return "The stop condition was reached.", state.stop_reason


def run_agent(data_dir: str | Path | None = None, max_iterations: int = 5) -> AgentState:
    base_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parent.parent / "data"
    state = AgentState(max_iterations=max_iterations)
    last_observation = "No observation yet."

    while not state.finished and state.iteration < state.max_iterations:
        actions, reason = _decide(state, last_observation)
        state.iteration += 1
        observation, decision = _execute(actions, state, base_dir)
        state.trace.append(
            TraceEntry(
                iteration=state.iteration,
                action=" → ".join(action.value for action in actions),
                observation=observation,
                decision=decision,
                reason=reason,
            )
        )
        last_observation = observation

    if not state.finished:
        state.finished = True
        state.stop_reason = f"Maximum iteration limit ({state.max_iterations}) reached."
        if state.trace:
            state.trace[-1].decision = f"STOP — {state.stop_reason}"
    return state

