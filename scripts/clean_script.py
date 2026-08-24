#!/usr/bin/env python3
"""Bereinigt das LLM-Skript fuer TTS: entfernt Label-Zeilen (HOOK:, Fakt 1:,
CTA:, ...), Fuehrungs-/Schlusszeichen und leere Zeilen. Es bleibt nur der
Sprechertext (mit Leerzeichen verbunden).

Usage:
    python scripts/clean_script.py <input.txt> <output.txt>
"""

import pathlib
import re
import sys

LABEL = re.compile(r"^(hook|fakt\s*\d+|punkt\s*\d+|cta|intro|outro|zitat|schlusssatz|uebergang|aufzaehlung\s*\d*)\s*:?", re.I)
BULLET = re.compile(r"^[\s*•·\-]+$")


def clean(text: str) -> str:
    parts = []
    for line in text.splitlines():
        s = line.strip()
        if not s or LABEL.match(s) or BULLET.match(s):
            continue
        s = s.strip('"“”„').lstrip("*•·-").strip()
        if s:
            parts.append(s)
    return " ".join(parts)


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python scripts/clean_script.py <input.txt> <output.txt>", file=sys.stderr)
        return 2
    src = pathlib.Path(sys.argv[1])
    dst = pathlib.Path(sys.argv[2])
    if not src.exists():
        print(f"missing: {src}", file=sys.stderr)
        return 1
    text = src.read_text(encoding="utf-8")
    cleaned = clean(text)
    dst.write_text(cleaned, encoding="utf-8")
    print(f"clean: {len(cleaned)} Zeichen (aus {len(text)} Zeichen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
