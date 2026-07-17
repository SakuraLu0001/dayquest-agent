"""Observation-driven local agent loop for DayQuest."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .akash_client import AkashClientError, AkashStoryClient
from .data_loader import DataLoadError, load_calendar, load_emails, load_transactions
from .models import Action, AgentState, Event, TraceEntry
from .privacy import redact_events
from .story import evaluate_story, generate_local_scenes, generate_story


LOADERS = {
    Action.READ_CALENDAR: ("calendar", load_calendar),
    Action.READ_TRANSACTIONS: ("transactions", load_transactions),
    Action.READ_EMAILS: ("emails", load_emails),
}

SAFE_FALLBACK_REASONS = {
    "scene_schema_failed": "The locally rendered scenes did not meet the required scene schema.",
    "privacy_validation_failed": "The motif-guided local story did not pass privacy validation.",
    "coverage_validation_failed": "The motif-guided local story did not meet the coverage requirement.",
    "read_timeout": "The AkashML response timed out while being read.",
    "connect_timeout": "The AkashML connection timed out.",
    "provider_error": "AkashML did not return a usable motif code.",
    "motif_code_invalid": "AkashML did not return exactly one allowed motif code.",
    "empty_response": "AkashML returned an empty motif response.",
}


def _safe_fallback_reason(error_type: str | None) -> str:
    return SAFE_FALLBACK_REASONS.get(
        error_type or "provider_error",
        "AkashML did not return a usable motif code.",
    )


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
        if state.selected_motif:
            provider_reason = "The previous observation applied an Akash-selected motif locally"
        elif state.provider_status["attempted"]:
            provider_reason = "The previous observation selected a safe local fallback after the AkashML attempt"
        else:
            provider_reason = "The previous observation selected the local story because AkashML was not configured"
        return [Action.EVALUATE_STORY, Action.STOP], (
            f"{provider_reason}; coverage and privacy must now be evaluated before the loop can stop."
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


def _execute(
    actions: list[Action],
    state: AgentState,
    data_dir: Path,
    story_client: AkashStoryClient | None,
) -> tuple[str, str]:
    if len(actions) == 1 and actions[0] in LOADERS:
        observation = _load(actions[0], state, data_dir)
        return observation, "Use this observation to choose the next unqueried source or begin safe synthesis."

    if Action.ANALYZE_TIMELINE in actions:
        state.events.sort(key=lambda event: event.start_time)
        state.missing_time_ranges = analyze_gaps(state.events)
        state.events, state.privacy_risks = redact_events(state.events)
        local_scenes = generate_local_scenes(state.events)
        if not local_scenes:
            state.finished = True
            state.stop_reason = "Stopped safely: fewer than three key events were available for a faithful story."
            return (
                f"Analyzed {len(state.events)} events and applied the privacy gate, but fewer than 3 story scenes were supportable.",
                "STOP without inventing unsupported events.",
            )

        state.scenes = local_scenes
        if story_client is not None and story_client.configured:
            state.provider_status["attempted"] = True
            try:
                remote_result = story_client.select_fantasy_motif(state.events)
            except AkashClientError as exc:
                state.provider_status.update(
                    {
                        "connected": False,
                        "used_for_story": False,
                        "fallback_used": True,
                        "http_status": exc.diagnostics.http_status,
                        "latency_ms": exc.diagnostics.latency_ms,
                        "error_type": exc.error_type,
                        "fallback_reason": _safe_fallback_reason(exc.error_type),
                        "remote_scene_count": None,
                        "remote_artifact_type": "motif_code",
                    }
                )
                provider_observation = (
                    f"Akash failed with {exc.error_type}; generated {len(local_scenes)} local fallback scenes."
                )
                provider_decision = "Use the local fallback, then evaluate coverage and privacy locally."
            else:
                state.selected_motif = remote_result.motif_code
                state.scenes = generate_local_scenes(
                    state.events,
                    motif_code=state.selected_motif,
                )
                state.provider_status.update(
                    {
                        "provider": "AkashML + local grounded renderer",
                        "connected": False,
                        "used_for_story": False,
                        "model": remote_result.model,
                        "http_status": remote_result.http_status,
                        "latency_ms": remote_result.latency_ms,
                        "request_id": remote_result.request_id,
                        "fallback_used": False,
                        "error_type": None,
                        "fallback_reason": None,
                        "remote_scene_count": None,
                        "remote_artifact_type": "motif_code",
                    }
                )
                provider_observation = f"AkashML selected the {state.selected_motif} motif."
                provider_decision = "Use the remote motif to drive the local grounded renderer."
        else:
            error_type = (
                story_client.configuration_error if story_client is not None else "missing_configuration"
            )
            state.provider_status["error_type"] = error_type
            state.provider_status["fallback_reason"] = _safe_fallback_reason(error_type)
            provider_observation = (
                f"AkashML was not configured ({error_type}); generated {len(local_scenes)} local fallback scenes."
            )
            provider_decision = "Use the local fallback, then evaluate coverage and privacy locally."
        return (
            f"Analyzed {len(state.events)} events, found {len(state.missing_time_ranges)} gaps, "
            f"handled {len(state.privacy_risks['Detected'])} privacy risks. {provider_observation}",
            provider_decision,
        )

    if Action.EVALUATE_STORY in actions:
        motif_pending = bool(
            state.selected_motif
            and state.provider_status["remote_artifact_type"] == "motif_code"
            and not state.provider_status["fallback_used"]
        )
        state.evaluation = evaluate_story(state.events, state.scenes)
        if not state.evaluation["passed"]:
            failed_remote_evaluation = dict(state.evaluation)
            state.scenes = generate_story(state.events, revision=True)
            state.evaluation = evaluate_story(state.events, state.scenes)
            state.evaluation["revised_once"] = True
            if motif_pending:
                if not failed_remote_evaluation["privacy_safe"]:
                    error_type = "privacy_validation_failed"
                elif failed_remote_evaluation["key_event_coverage"] < 0.75:
                    error_type = "coverage_validation_failed"
                else:
                    error_type = "scene_schema_failed"
                state.provider_status.update(
                    {
                        "provider": "AkashML",
                        "connected": False,
                        "used_for_story": False,
                        "fallback_used": True,
                        "error_type": error_type,
                        "fallback_reason": _safe_fallback_reason(error_type),
                    }
                )
                state.selected_motif = ""
        elif motif_pending:
            state.provider_status.update(
                {
                    "connected": True,
                    "used_for_story": True,
                }
            )
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


def run_agent(
    data_dir: str | Path | None = None,
    max_iterations: int = 5,
    story_client: AkashStoryClient | None = None,
) -> AgentState:
    base_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parent.parent / "data"
    state = AgentState(max_iterations=max_iterations)
    if story_client is not None:
        state.provider_status["configured"] = story_client.configured
        state.provider_status["model"] = story_client.config.model
        state.provider_status["error_type"] = story_client.configuration_error
    last_observation = "No observation yet."

    while not state.finished and state.iteration < state.max_iterations:
        actions, reason = _decide(state, last_observation)
        state.iteration += 1
        observation, decision = _execute(actions, state, base_dir, story_client)
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
