"""Tests for video/generate (continuum realistic-video recipe)."""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).parent.parent
BASE_IMAGE = pathlib.Path(r"C:\OmniRoute\ComfyUI\output\user_test_360_00001_.png")
if not BASE_IMAGE.exists():
    BASE_IMAGE = REPO / "data" / "money_printer_pruned" / "image_0.png"


def run_helper(*args):
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "video_generate.py"), *args],
        capture_output=True, text=True, cwd=REPO, check=False,
    )


def test_helper_exists():
    p = REPO / "scripts" / "video_generate.py"
    assert p.exists(), "helper scripts/video_generate.py missing"
    content = p.read_text(encoding="utf-8")
    assert "ken-burns" in content
    assert "ANGLES" in content


def test_types_exist():
    p = REPO / "src" / "commands" / "video" / "generate" / "shared" / "VideoGenerateTypes.ts"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "video/generate" in content
    assert "generateVideo" in content


def test_server_and_browser_commands_exist():
    server = REPO / "src" / "commands" / "video" / "generate" / "server" / "VideoGenerateServerCommand.ts"
    browser = REPO / "src" / "commands" / "video" / "generate" / "browser" / "VideoGenerateBrowserCommand.ts"
    assert server.exists()
    assert browser.exists()
    assert "video/generate" in server.read_text(encoding="utf-8")
    assert "video/generate" in browser.read_text(encoding="utf-8")


def test_spec_exists():
    p = REPO / "tools" / "generator" / "specs" / "video-generate.json"
    assert p.exists(), "generator spec tools/generator/specs/video-generate.json missing"
    spec = json.loads(p.read_text(encoding="utf-8"))
    assert spec["name"] == "video/generate"
    assert spec["accessLevel"] == "ai-safe"


def test_dry_run_validates():
    assert BASE_IMAGE.exists(), f"base image missing: {BASE_IMAGE}"
    r = run_helper("--base-image", str(BASE_IMAGE), "--prompt", "360 degree turn",
                   "--frames", "6", "--fps", "24", "--dry-run")
    assert r.returncode == 0, f"dry-run failed: {r.stdout} {r.stderr}"
    out = json.loads(r.stdout)
    assert out["success"] is True
    assert out["dryRun"] is True


def test_dry_run_rejects_missing_base_image():
    r = run_helper("--base-image", r"C:\nonexistent\missing.png", "--dry-run")
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["success"] is False
    assert "not found" in out["error"]


def test_dry_run_accepts_base_images_array():
    """--base-images (Array-Support): alle Bilder in einem Lauf, Frames = images * frames."""
    assert BASE_IMAGE.exists()
    r = run_helper("--base-images", f"{BASE_IMAGE},{BASE_IMAGE}",
                   "--prompt", "cinematic pan", "--frames", "6", "--fps", "24", "--dry-run")
    assert r.returncode == 0, f"array dry-run failed: {r.stdout} {r.stderr}"
    out = json.loads(r.stdout)
    assert out["success"] is True
    assert out["images"] == 2
    assert out["frames"] == 12


def test_base_images_preferred_over_base_image():
    """Wenn beides gesetzt: --base-images gewinnt."""
    r = run_helper("--base-image", str(BASE_IMAGE),
                   "--base-images", f"{BASE_IMAGE},{BASE_IMAGE},{BASE_IMAGE}", "--dry-run")
    assert r.returncode == 0
    assert json.loads(r.stdout)["images"] == 3


def test_base_images_rejects_missing_entry():
    r = run_helper("--base-images", f"{BASE_IMAGE},C:\\nonexistent\\x.png", "--dry-run")
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["success"] is False
    assert "not found" in out["error"]


def test_missing_base_args_fails():
    r = run_helper("--dry-run")
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["success"] is False
    assert "base-image" in out["error"]


def test_model_detection_fallback():
    """minimax-h3/zImageTurbo files are not downloaded -> ken-burns fallback."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("video_generate", REPO / "scripts" / "video_generate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    available, found = mod.model_files_available("minimax-h3")
    assert isinstance(available, bool)
    # If model files exist this is an integration-ready environment; otherwise fallback kicks in.
    if not available:
        assert found == []
    assert mod.DEFAULT_CHECKPOINT.endswith(".safetensors")


def test_angle_choreography_has_six_entries():
    import importlib.util
    spec = importlib.util.spec_from_file_location("video_generate", REPO / "scripts" / "video_generate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert len(mod.ANGLES) == 6
    names = [a[0] for a in mod.ANGLES]
    assert names == ["front", "turn-right", "back", "turn-left", "wave", "front-close"]
