"""Validates that money-printer-realistic.json wires to real commands with correct params."""
import json
import pathlib

REPO = pathlib.Path(__file__).parent.parent
RECIPE = REPO / "src" / "recipes" / "money-printer-realistic.json"
KNOWN = {"rag/build", "ai/should-respond", "ai/generate", "tts/speak",
         "image/generate-realistic", "video/generate", "ffmpeg_tiktok",
         "artifacts/store", "youtube/upload"}


def load_recipe():
    return json.loads(RECIPE.read_text(encoding="utf-8"))


def test_recipe_commands_exist():
    recipe = load_recipe()
    for step in recipe["pipeline"]:
        assert step["command"] in KNOWN, f"unbekanntes Command: {step['command']}"


def test_recipe_command_dirs_exist():
    recipe = load_recipe()
    for step in recipe["pipeline"]:
        cmd = step["command"]
        if cmd in ("rag/build", "ai/should-respond", "ai/generate", "ffmpeg_tiktok", "youtube/upload"):
            continue
        parts = cmd.split("/")
        assert pathlib.Path(REPO, "src", "commands", *parts).exists(), f"Command-Verzeichnis fehlt: {cmd}"


def test_tts_step_has_kokoro_and_voicebox_fallback():
    recipe = load_recipe()
    tts = next(s for s in recipe["pipeline"] if s["command"] == "tts/speak")
    assert tts["params"]["engine"] == "kokoro"
    assert tts["params"]["fallbackEngine"] == "voicebox"
    assert tts["params"]["profile"] == "Overlay DE"


def test_video_step_fallback_ken_burns():
    recipe = load_recipe()
    vid = next(s for s in recipe["pipeline"] if s["command"] == "video/generate")
    assert vid["params"]["fallback"] == "ken-burns"
    assert "optional" not in vid["params"]
