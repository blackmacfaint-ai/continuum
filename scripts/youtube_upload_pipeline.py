#!/usr/bin/env python3
"""Money-Printer Step 7: YouTube Short-Upload.

Nutzt die bereits verifizierte Upload-Pipeline `orca/youtube.py` aus
voice-agents (OAuth-Credentials + Refresh-Token in
C:\\OmniRoute\\voice-agents\\.env bzw. client_secrets.json), damit keine
zweiten Google-Credentials oder zusaetzlichen Pakete noetig sind.

Usage:
  python scripts/youtube_upload_pipeline.py --video <tiktok.mp4> --topic "Hamburger Hafen"
  python scripts/youtube_upload_pipeline.py --video <tiktok.mp4> --topic "..." --privacy unlisted --dry-run

Output: JSON {"success": true, "videoId": ..., "url": ...} auf stdout.
Exit 0 = Erfolg, 1 = Upload fehlgeschlagen, 2 = kein Video/kein Skript.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

PROJECT_DIR = pathlib.Path(__file__).resolve().parent.parent
VA_ROOT = pathlib.Path(os.environ.get("VOICE_AGENTS_ROOT", r"C:\OmniRoute\voice-agents"))
VA_PY = VA_ROOT / ".venv" / "Scripts" / "python.exe"
SCRIPT_TXT = PROJECT_DIR / "data" / "audio" / "script_clean.txt"
SCRIPT_TXT_FALLBACK = PROJECT_DIR / "data" / "audio" / "script.txt"
OLLAMA_URL = "http://localhost:11434/api/chat"
LLM_MODELS = ["hf.co/Jackrong/Qwen3.5-9B-DeepSeek-V4-Flash-GGUF:Q4_K_M", "llama3.1:8b-instruct-q4_K_M", "gemma4:26b"]


def _parse_json(text: str) -> dict:
    """Robustes Parsen: ganzes Output, sonst erstes { bis letztes }."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return {"raw": text}


def _read_script() -> str:
    for p in (SCRIPT_TXT, SCRIPT_TXT_FALLBACK):
        if p.exists():
            try:
                return p.read_text(encoding="utf-8", errors="ignore").strip()
            except OSError:
                continue
    return ""


def _llm_chat(prompt: str) -> str:
    """Ollama-Call mit Fallback-Kette (wie ai_generate.py). Liefert Text oder ""."""
    messages = [
        {"role": "system", "content": "Du bist ein professioneller deutscher YouTube-Autor fuer Shorts."},
        {"role": "user", "content": prompt},
    ]
    for model in LLM_MODELS:
        body = json.dumps({
            "model": model, "messages": messages, "stream": False,
            "options": {"temperature": 0.7, "num_predict": 300},
        }).encode()
        req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                text = ((json.load(r).get("message") or {}).get("content") or "").strip()
            if text:
                return text
        except Exception:
            continue
    return ""


def _parse_meta(content: str) -> dict:
    """Extrahiert Titel/Beschreibung/Tags aus der LLM-Antwort (Zeilen 'Titel:', 'Beschreibung:', 'Tags:')."""
    meta = {"title": "", "description": "", "tags": []}
    if not content:
        return meta
    for line in content.splitlines():
        s = line.strip()
        low = s.lower()
        for key in ("titel", "title", "beschreibung", "description", "tags"):
            if low.startswith(key + ":"):
                val = s.split(":", 1)[1].strip().strip('"\u201C\u201D')
                if key in ("titel", "title"):
                    meta["title"] = val
                elif key in ("beschreibung", "description"):
                    meta["description"] = val
                elif key == "tags":
                    meta["tags"] = [t.strip() for t in val.split(",") if t.strip()]
    return meta


def _llm_meta(script: str, topic: str) -> dict:
    """Generiert Titel/Beschreibung/Tags per LLM aus dem Skript. Leer bei Fehler."""
    prompt = (
        "Erzeuge Titel, Beschreibung und Tags fuer dieses deutsche YouTube-Short-Skript:\n\n"
        f"{script[:1200]}\n\n"
        "Antworte NUR in diesem Format, keine Erklaerungen:\n"
        "Titel: <max 60 Zeichen, deutsch, neugierig machend, YouTube-Style, KEINE Hashtags>\n"
        "Beschreibung: <1-3 Saetze deutsch, am Ende 3-5 passende Hashtags>\n"
        "Tags: <5-8 Stichworte, kommagetrennt, deutsch>"
    )
    content = _llm_chat(prompt)
    meta = _parse_meta(content)
    if not meta["title"] and topic:
        meta["title"] = _topic_title(topic)
    return meta


def _topic_title(topic: str) -> str:
    """Erzeugt einen YouTube-tauglichen Titel aus dem Topic (max ~60 Zeichen)."""
    t = topic.split(",")[0].strip().strip(".").strip()
    t = " ".join(t.split())
    if not t:
        t = "Money Printer Short"
    return t[:60]


def _description(script_txt: pathlib.Path, topic: str) -> str:
    lines = []
    if script_txt.exists():
        text = script_txt.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            lines.append(text[:500])
    lines.append(f"Thema: {topic}")
    lines.append("#shorts #moneyprinter #faceless")
    return "\n\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="YouTube-Upload als Money-Printer-Pipeline-Schritt.")
    ap.add_argument("--video", required=True, help="Pfad zur fertigen tiktok.mp4")
    ap.add_argument("--topic", default="", help="Thema/Topic (Fallback fuer Titel)")
    ap.add_argument("--privacy", default="unlisted", choices=["public", "private", "unlisted"])
    ap.add_argument("--no-llm-title", action="store_true", help="Titel/Beschreibung/Tags NICHT per LLM generieren")
    ap.add_argument("--dry-run", action="store_true", help="Nur Argumente pruefen, kein Upload")
    args = ap.parse_args()

    video = pathlib.Path(args.video).resolve()  # absolut, unabhaengig vom cwd des orca.youtube-Subprozesses
    if not video.is_file():
        print(json.dumps({"success": False, "error": f"Video nicht gefunden: {video}"}))
        return 2
    if not VA_PY.exists():
        print(json.dumps({"success": False, "error": f"voice-agents venv fehlt: {VA_PY}"}))
        return 2

    title = _topic_title(args.topic)
    description = _description(SCRIPT_TXT, args.topic)
    tags: list[str] = []
    if not args.no_llm_title:
        script = _read_script()
        if script:
            print(f"LLM: generiere Titel/Beschreibung/Tags aus Skript ({len(script)} Zeichen) ...", file=sys.stderr)
            meta = _llm_meta(script, args.topic)
            if meta.get("title"):
                title = meta["title"]
            if meta.get("description"):
                description = meta["description"]
            tags = meta.get("tags") or []
            print(f"LLM: Titel={title!r} Tags={tags}", file=sys.stderr)
        else:
            print("LLM: kein Skript gefunden, nutze Topic-Fallback", file=sys.stderr)

    if args.dry_run:
        print(json.dumps({
            "success": True, "dryRun": True,
            "video": str(video), "title": title, "description": description[:80],
            "tags": tags, "privacy": args.privacy,
        }))
        return 0

    # Upload mit 3 Versuchen + Backoff (Netz-/API-Fehler abfangen)
    last_err = ""
    for attempt in range(1, 4):
        try:
            cmd = [
                str(VA_PY), "-m", "orca.youtube",
                str(video), title,
                "--description", description,
                "--privacy", args.privacy,
            ]
            if tags:
                cmd += ["--tags"] + tags[:15]
            r = subprocess.run(
                cmd,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=1200, cwd=str(VA_ROOT),
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            out = (r.stdout or "").strip()
            if r.returncode == 0 and out:
                info = _parse_json(out)
                info["success"] = bool(info.get("videoId"))
                print(json.dumps(info, ensure_ascii=False))
                return 0 if info["success"] else 1
            last_err = (r.stderr or out or f"Exit {r.returncode}")[-400:]
        except subprocess.TimeoutExpired:
            last_err = "Upload-Zeitueberschreitung (>20 min)"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        if attempt < 3:
            time.sleep(2 ** attempt)

    print(json.dumps({"success": False, "error": last_err[-400:]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
