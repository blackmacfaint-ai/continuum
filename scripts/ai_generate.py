#!/usr/bin/env python3
"""ai/generate helper - deutsches faceless-Skript via lokales Ollama (Qwen3.5-9B GGUF).

Usage:
  python scripts/ai_generate.py --prompt "Schreibe ein 150-Woerter deutsches faceless TikTok-Skript ..."
  python scripts/ai_generate.py --prompt "..." --model hf.co/Jackrong/Qwen3.5-9B-DeepSeek-V4-Flash-GGUF:Q4_K_M

Prints JSON: {"success": true, "text": "...", "words": 150}
"""
import argparse
import json
import sys
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "hf.co/Jackrong/Qwen3.5-9B-DeepSeek-V4-Flash-GGUF:Q4_K_M"


def parse_args():
    ap = argparse.ArgumentParser(description="Generate German script via local Ollama")
    ap.add_argument("--prompt", required=True, help="Prompt for the script")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--temperature", type=float, default=0.6)
    ap.add_argument("--max-tokens", type=int, default=500)
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    if not args.prompt.strip():
        print(json.dumps({"success": False, "error": "prompt is required"}))
        return 1
    if args.dry_run:
        print(json.dumps({"success": True, "text": "", "words": 0, "dryRun": True}))
        return 0

    # System-Prompt ist Pflicht: Qwen3.5-GGUFs liefern ohne ihn bei grossem num_predict
    # leere Antworten (done_reason=length, content leer). Fallback-Kette als Absicherung.
    fallbacks = ["llama3.1:8b-instruct-q4_K_M", "gemma4:26b"]
    candidates = [args.model] + [m for m in fallbacks if m != args.model]
    messages = [
        {"role": "system", "content": "Du bist ein professioneller deutscher Autor fuer faceless TikTok-Skripte."},
        {"role": "user", "content": args.prompt},
    ]
    used = None
    text = ""
    for model in candidates:
        body = json.dumps({
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": args.temperature, "num_predict": args.max_tokens},
        }).encode()
        req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.load(r)
        except urllib.error.URLError as e:
            print(json.dumps({"success": False, "error": f"ollama unreachable: {e}"}))
            return 1
        text = (data.get("message") or {}).get("content", "").strip()
        if text:
            used = model
            break
    if not text:
        print(json.dumps({"success": False, "error": "ollama returned empty response for all models"}))
        return 1
    print(json.dumps({"success": True, "text": text, "words": len(text.split()), "model": used}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
