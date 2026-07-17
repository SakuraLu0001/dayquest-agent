from dayquest.models import Scene
from dayquest.story_reel import motif_theme, render_story_reel_html


def scenes(count):
    return [Scene(i, f"Chapter {i}", "afternoon", "fantasy", f"Narration {i}", [f"internal-{i}"], "safe") for i in range(1, count + 1)]


def test_three_scenes_generate_reel():
    reel = render_story_reel_html(scenes(3), "RUNE_STORM")
    assert reel.count("data-scene=") == 3 and "show(0)" in reel and "theme-rune" in reel


def test_reel_shows_at_most_five():
    reel = render_story_reel_html(scenes(7))
    assert reel.count("data-scene=") == 5 and "Chapter 6" not in reel


def test_scene_text_is_escaped():
    scene = scenes(1)[0]
    scene.title = '<script>alert("x")</script>'
    scene.narration = '<img src=x onerror="x"> & text'
    reel = render_story_reel_html([scene])
    assert "&lt;script&gt;" in reel and "&lt;img" in reel and "&amp; text" in reel
    assert '<script>alert("x")</script>' not in reel and '<img src=x' not in reel


def test_motif_theme_mapping_and_default():
    assert [motif_theme(x) for x in ("MIST_GATE", "CLOCKWORK_TRIAL", "RUNE_STORM", "SKY_CARAVAN", "MIRROR_SPIRIT")] == ["mist", "clockwork", "rune", "sky", "mirror"]
    assert motif_theme("UNKNOWN") == "default"


def test_short_story_uses_static_fallback():
    reel = render_story_reel_html(scenes(2))
    assert " static" in reel and "setTimeout" not in reel


def test_empty_story_uses_safe_message():
    assert "Story reel will appear" in render_story_reel_html([])


def test_counter_dots_and_replay_exist():
    reel = render_story_reel_html(scenes(4))
    assert "Scene 1 / 4" in reel and reel.count("data-dot=") == 4
    assert "Replay Story Reel" in reel and "replayStoryReel" in reel and "clearTimeout" in reel


def test_no_external_assets_or_internal_ids():
    reel = render_story_reel_html(scenes(3))
    assert "http://" not in reel and "https://" not in reel and "<script src=" not in reel
    assert "cdn" not in reel.lower() and "internal-1" not in reel
