#!/usr/bin/env python3
"""tts/speak helper - Kokoro-DE (8881, martin) mit Voicebox-Fallback (17493, 'Overlay DE').

Usage:
  python scripts/tts_speak.py --text "Hallo Welt" --voice martin --engine kokoro --fallback-engine voicebox
  python scripts/tts_speak.py --text "..." --engine voicebox --profile "Overlay DE" --output C:/tmp/voice.wav

Prints a JSON result on stdout:
  {"success": true, "audioPath": "...", "engine": "kokoro", "duration": 2.36}
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

KOKORO_URL = "http://localhost:8881/v1/audio/speech"
VOICEBOX_URL = "http://127.0.0.1:17493"
REPO_ROOT = pathlib.Path(__file__).parent.parent


def parse_args():
    ap = argparse.ArgumentParser(description="TTS: Kokoro-DE mit Voicebox-Fallback")
    ap.add_argument("--text", required=True, help="Text to synthesize")
    ap.add_argument("--voice", default="martin", help="Kokoro voice")
    ap.add_argument("--engine", choices=["kokoro", "voicebox"], default="kokoro")
    ap.add_argument("--fallback-engine", choices=["kokoro", "voicebox", "none"], default="voicebox")
    ap.add_argument("--lang", default="de")
    ap.add_argument("--profile", default="Overlay DE", help="Voicebox profile name")
    ap.add_argument("--output", default=None, help="Output audio path (default data/audio/voice.wav)")
    ap.add_argument("--dry-run", action="store_true", help="Validate args without synthesizing")
    return ap.parse_args()


def kokoro_speak(text: str, voice: str, out_path: pathlib.Path) -> pathlib.Path:
    body = json.dumps({"text": text, "voice": voice, "response_format": "mp3"}).encode()
    req = urllib.request.Request(KOKORO_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    out_path.write_bytes(data)
    return out_path


def voicebox_speak(text: str, profile: str, out_path: pathlib.Path) -> pathlib.Path:
    gen = json.dumps({"text": text, "profile": profile}).encode()
    req = urllib.request.Request(VOICEBOX_URL + "/generate", data=gen, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    gid = data.get("generation_id") or data.get("id")
    if not gid:
        raise RuntimeError("voicebox /generate returned no id")
    for _ in range(120):
        time.sleep(3)
        try:
            with urllib.request.urlopen(VOICEBOX_URL + f"/history/{gid}", timeout=10) as r:
                h = json.load(r)
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            continue
        if h.get("status") == "completed":
            break
    with urllib.request.urlopen(VOICEBOX_URL + f"/audio/{gid}", timeout=30) as r:
        out_path.write_bytes(r.read())
    return out_path


def main() -> int:
    args = parse_args()
    if not args.text.strip():
        print(json.dumps({"success": False, "error": "text is required"}))
        return 1
    out = pathlib.Path(args.output) if args.output else (REPO_ROOT / "data" / "audio" / "voice.wav")
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        print(json.dumps({"success": True, "audioPath": str(out), "engine": args.engine, "dryRun": True}))
        return 0

    tts_errors = (urllib.error.URLError, OSError, json.JSONDecodeError, RuntimeError, KeyError)
    engine = args.engine
    try:
        if engine == "kokoro":
            kokoro_speak(args.text, args.voice, out)
        else:
            voicebox_speak(args.text, args.profile, out)
    except tts_errors as e:
        if args.fallback_engine == "none":
            print(json.dumps({"success": False, "error": f"{engine}: {e}"}))
            return 1
        print(f"WARN {engine} failed ({e}), fallback to {args.fallback_engine}", file=sys.stderr)
        engine = args.fallback_engine
        try:
            if engine == "kokoro":
                kokoro_speak(args.text, args.voice, out)
            else:
                voicebox_speak(args.text, args.profile, out)
        except tts_errors as e2:
            print(json.dumps({"success": False, "error": f"{engine}: {e2}"}))
            return 1

    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    print(json.dumps({"success": True, "audioPath": str(out), "engine": engine,
                      "duration": float(dur) if dur else None}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
