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
}


def _time_bucket(iso_time: str) -> str:
    hour = int(iso_time[11:13])
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def generate_story(events: list[Event], revision: bool = False) -> list[Scene]:
    """Create one scene per key event, ignoring email bodies and exact evidence."""
    candidates = [event for event in events if event.event_type in SCENE_TEMPLATES]
    candidates.sort(key=lambda event: event.start_time)
    scenes: list[Scene] = []
    for event in candidates[:5]:
        title, fictional_event, narration, embellishment = SCENE_TEMPLATES[event.event_type]
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


def evaluate_story(events: list[Event], scenes: list[Scene]) -> dict[str, object]:
    key_events = [event for event in events if event.event_type in SCENE_TEMPLATES]
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

