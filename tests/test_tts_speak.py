"""Tests for tts/speak (Kokoro-DE + Voicebox fallback)."""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).parent.parent


def run_helper(*args):
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "tts_speak.py"), *args],
        capture_output=True, text=True, cwd=REPO, check=False,
    )


def test_helper_exists():
    p = REPO / "scripts" / "tts_speak.py"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "kokoro" in content and "voicebox" in content


def test_types_exist():
    p = REPO / "src" / "commands" / "tts" / "speak" / "shared" / "TtsSpeakTypes.ts"
    content = p.read_text(encoding="utf-8")
    assert "tts/speak" in content
    assert "ttsSpeak" in content


def test_spec_exists():
    p = REPO / "tools" / "generator" / "specs" / "tts-speak.json"
    spec = json.loads(p.read_text(encoding="utf-8"))
    assert spec["name"] == "tts/speak"
    assert spec["accessLevel"] == "ai-safe"


def test_dry_run_rejects_missing_text():
    r = run_helper("--text", "", "--dry-run")
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["success"] is False and "text" in out["error"]


def test_dry_run_ok():
    r = run_helper("--text", "Hallo Welt", "--dry-run")
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["success"] is True and out["dryRun"] is True
