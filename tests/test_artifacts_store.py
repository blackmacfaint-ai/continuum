"""Tests for artifacts/store (artifact registry)."""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).parent.parent


def run_helper(*args):
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "artifacts_store.py"), *args],
        capture_output=True, text=True, cwd=REPO, check=False,
    )


def test_helper_exists():
    assert (REPO / "scripts" / "artifacts_store.py").exists()


def test_types_exist():
    p = REPO / "src" / "commands" / "artifacts" / "store" / "shared" / "ArtifactsStoreTypes.ts"
    content = p.read_text(encoding="utf-8")
    assert "artifacts/store" in content
    assert "storeArtifact" in content


def test_spec_exists():
    p = REPO / "tools" / "generator" / "specs" / "artifacts-store.json"
    spec = json.loads(p.read_text(encoding="utf-8"))
    assert spec["name"] == "artifacts/store"


def test_store_registers_artifact(tmp_path):
    art = tmp_path / "clip.mp4"
    art.write_bytes(b"\x00" * 2048)
    reg = tmp_path / "registry.json"
    r = run_helper("--artifact", str(art), "--type", "video", "--registry", str(reg))
    assert r.returncode == 0, f"{r.stdout} {r.stderr}"
    out = json.loads(r.stdout)
    assert out["success"] is True and out["artifactId"]
    entries = json.loads(reg.read_text(encoding="utf-8"))
    assert len(entries) == 1
    assert entries[0]["type"] == "video"
    assert entries[0]["artifactId"] == out["artifactId"]
    stored = pathlib.Path(entries[0]["path"])
    assert stored.exists() and stored.stat().st_size == 2048


def test_store_rejects_missing_file():
    r = run_helper("--artifact", r"C:\nonexistent\missing.mp4", "--type", "video")
    assert r.returncode == 1
    assert json.loads(r.stdout)["success"] is False
