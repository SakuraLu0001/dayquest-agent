"""Privacy-safe, deterministic high-fantasy story generation."""

from __future__ import annotations

from .models import Event, Scene
from .privacy import contains_forbidden_data


SCENE_TEMPLATES = {
    "language_exam": (
        "The Trial of Tongues",
        "Adventurers’ Guild language and diplomacy certification trial",
        "At the guild hall, the traveler faced a measured trial of words and diplomacy, earning passage to the next chapter of the quest.",
        "The examiners are portrayed as guild lorekeepers.",
    ),
    "coffee": (
        "Rest at the Roadside Tavern",
        "Rest and provisions at a roadside tavern",
        "The traveler paused for modest provisions, restored their focus, and reviewed the route ahead.",
        "The café is reimagined as a welcoming tavern.",
    ),
    "lunch": (
        "Rest at the Roadside Tavern",
        "Rest and provisions at a roadside tavern",
        "The traveler paused for modest provisions, restored their focus, and reviewed the route ahead.",
        "The meal is reimagined as tavern provisions.",
    ),
    "travel": (
        "The Caravan Crossing",
        "Journey by city caravan",
        "A city caravan carried the traveler toward the gathering place, bridging the quiet interval between two trials.",
        "Ordinary local travel becomes a caravan journey.",
    ),
    "hackathon": (
        "Challenge of the Artificers’ Forge",
        "Artificers’ Forge autonomous construct competition",
        "Among teams of artificers, the traveler entered a forge of ideas and helped shape an autonomous construct before the final bell.",
        "Software builders and agents are depicted as artificers and constructs.",
    ),
    "scheduled_event": (
        "The Gathering on the Quest Map",
        "A scheduled gathering at a guild hall",
        "The traveler followed the day's map to a planned gathering, where the next stage of the quest came into view.",
        "The scheduled event is portrayed as a gathering marked on a quest map.",
    ),
    "build_milestone": (
        "The Artificer's Workbench",
        "A grounded invention milestone at an artificer's workbench",
        "At the workbench, the traveler shaped another verified part of the construct and moved the build forward.",
        "The software milestone is reimagined as careful work on a magical construct.",
    ),
    "validation_milestone": (
        "The Construct's Trial",
        "A validation trial for the newly built construct",
        "The construct passed its recorded trial, giving the traveler confidence that the day's work remained sound.",
        "Automated validation is portrayed as a formal guild trial.",
    ),
    "challenge_resolution": (
        "The Mended Illusion",
        "Discovery and repair of a troublesome illusion",
        "The traveler found an interface-like illusion, corrected it, and restored clarity to the quest display.",
        "The verified bug fix becomes the repair of a harmless magical illusion.",
    ),
    "integration_milestone": (
        "The Allied Sigil",
        "A verified alliance between the construct and an external guild",
        "The traveler connected an outside guild's power to the construct, adding a new verified capability to the quest.",
        "The external integration is portrayed as an allied guild sigil.",
    ),
}

CANONICAL_EVENT_CATEGORIES = {
    "calendar_event": "scheduled_event",
    "repository_created": "build_milestone",
    "agent_milestone": "build_milestone",
    "test_result": "validation_milestone",
    "bug_fix": "challenge_resolution",
    "sponsor_integration": "integration_milestone",
    "event_confirmation": "supporting_evidence",
    "email_metadata": "supporting_evidence",
}

MOTIF_STYLES = {
    "MIST_GATE": (
        "Beyond the Mist Gate",
        "Pale mist and a recurring moonlit gate frame the unknown journey.",
        "Mist and doorways are fictional signs of crossing into the next challenge.",
    ),
    "CLOCKWORK_TRIAL": (
        "The Clockwork Trial",
        "Brass gears recur as the mechanical guild tests an orderly automatic construct.",
        "The recurring gears and clockwork guild are fictional symbols of disciplined invention.",
    ),
    "RUNE_STORM": (
        "The Rune Storm",
        "Glowing runes spiral through a recurring violet storm as the traveler restores order.",
        "The rune storm is a fictional metaphor for disruption resolved through careful work.",
    ),
    "SKY_CARAVAN": (
        "The Sky Caravan",
        "Silver sails recur above an airborne caravan bound between distant guilds.",
        "The sky caravan and its silver sails fictionalize the day's connected journeys.",
    ),
    "MIRROR_SPIRIT": (
        "The Mirror Spirit",
        "A recurring mirror spirit reveals interface-like illusions that can be found and repaired.",
        "The mirror spirit is a fictional guide for noticing and correcting anomalies.",
    ),
}


def _time_bucket(iso_time: str) -> str:
    hour = int(iso_time[11:13])
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def canonical_event_category(event_type: str) -> str:
    """Map a normalized type to a local story category without changing the event."""
    return CANONICAL_EVENT_CATEGORIES.get(event_type, event_type)


def is_story_event(event: Event) -> bool:
    """Return whether a factual event can independently anchor a story scene."""
    return canonical_event_category(event.event_type) in SCENE_TEMPLATES


def story_event_candidates(events: list[Event]) -> list[Event]:
    """Choose up to five chronological factual anchors for the grounded story."""
    candidates = [event for event in events if is_story_event(event)]
    candidates.sort(key=lambda event: event.start_time)
    return candidates[:5]


def generate_local_scenes(
    events: list[Event],
    motif_code: str | None = None,
    revision: bool = False,
) -> list[Scene]:
    """Render grounded scenes locally, optionally guided by an allowlisted motif."""
    candidates = story_event_candidates(events)
    motif = MOTIF_STYLES.get(motif_code or "")
    scenes: list[Scene] = []
    for event in candidates:
        category = canonical_event_category(event.event_type)
        title, fictional_event, narration, embellishment = SCENE_TEMPLATES[category]
        if motif:
            motif_title, motif_atmosphere, motif_embellishment = motif
            title = f"{title} — {motif_title}"
            narration += f" {motif_atmosphere}"
            if not scenes:
                embellishment += f" {motif_embellishment}"
        if revision:
            narration += " The chronicle keeps only the verified outline of that moment."
        scenes.append(
            Scene(
                scene_number=len(scenes) + 1,
                title=title,
                approximate_time=_time_bucket(event.start_time),
                fictional_event=fictional_event,
                narration=narration,
                based_on_event_ids=[event.event_id],
                fictional_embellishment=embellishment,
            )
        )
    return scenes if len(scenes) >= 3 else []


def generate_story(events: list[Event], revision: bool = False) -> list[Scene]:
    """Backward-compatible entry point for the fully local renderer."""
    return generate_local_scenes(events, revision=revision)


def evaluate_story(events: list[Event], scenes: list[Scene]) -> dict[str, object]:
    key_events = story_event_candidates(events)
    covered = {event_id for scene in scenes for event_id in scene.based_on_event_ids}
    required = {event.event_id for event in key_events}
    story_text = " ".join(
        f"{scene.title} {scene.fictional_event} {scene.narration} {scene.fictional_embellishment}"
        for scene in scenes
    )
    privacy_safe = not contains_forbidden_data(story_text)
    coverage = len(required & covered) / len(required) if required else 0.0
    passed = len(scenes) >= 3 and coverage >= 0.75 and privacy_safe
    return {
        "passed": passed,
        "scene_count": len(scenes),
        "key_event_coverage": round(coverage, 2),
        "privacy_safe": privacy_safe,
        "covered_event_ids": sorted(required & covered),
    }
