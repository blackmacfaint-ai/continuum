"""E2E smoke test for the money-printer production chain (dry-run level)."""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).parent.parent


def run(name, *args):
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / name), *args],
        capture_output=True, text=True, cwd=REPO, check=False,
    )


def test_e2e_dry_run_chain():
    base = REPO / "data" / "money_printer_pruned" / "image_0.png"
    assert base.exists(), "data/money_printer_pruned/image_0.png missing - run image pipeline first"

    r1 = run("video_generate.py", "--base-image", str(base), "--frames", "6", "--fps", "24", "--dry-run")
    assert r1.returncode == 0, f"video_generate dry-run: {r1.stdout} {r1.stderr}"
    assert json.loads(r1.stdout)["dryRun"] is True

    r2 = run("tts_speak.py", "--text", "Hallo, dies ist ein Test.", "--dry-run")
    assert r2.returncode == 0, f"tts_speak dry-run: {r2.stdout} {r2.stderr}"
    assert json.loads(r2.stdout)["dryRun"] is True

    r3 = run("artifacts_store.py", "--artifact", str(base), "--type", "image", "--dry-run")
    assert r3.returncode == 0, f"artifacts_store dry-run: {r3.stdout} {r3.stderr}"
    assert json.loads(r3.stdout)["dryRun"] is True


def test_e2e_helpers_exist():
    for name in ("video_generate.py", "tts_speak.py", "artifacts_store.py"):
        assert (REPO / "scripts" / name).exists(), f"scripts/{name} missing"


def test_e2e_recipe_pipeline_commands_present():
    recipe = json.loads((REPO / "src" / "recipes" / "money-printer-realistic.json").read_text(encoding="utf-8"))
    commands = [s["command"] for s in recipe["pipeline"]]
    for needed in ("ai/generate", "tts/speak", "image/generate-realistic", "video/generate",
                   "ffmpeg_tiktok", "artifacts/store", "youtube/upload"):
        assert needed in commands, f"Rezept-Step fehlt: {needed}"
