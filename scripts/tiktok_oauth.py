#!/usr/bin/env python3
"""TikTok OAuth 2.0 Setup — erzeugt Authorization-URL, tauscht Code gegen Token.

Einmaliger Setup-Flow:
1. Script zeigt eine URL an
2. Öffne sie im Browser, logge dich ein, autorisiere die App
3. Callback zeigt den Code auf der GitHub-Pages-Seite
4. Trage den Code hier ein oder übergebe ihn als Argument
5. Script speichert Access- + Refresh-Token in .env

Danach: tiktok_upload.py nutzt den Refresh-Token automatisch.

Usage:
  python scripts/tiktok_oauth.py                  # interaktiv
  python scripts/tiktok_oauth.py --code <CODE>    # non-interaktiv
"""

import argparse
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

PROJECT_DIR = pathlib.Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_DIR / ".env"
ENV_EXAMPLE = PROJECT_DIR / ".env.example"

TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
SCOPES = "user.info.basic,video.upload,video.publish"


def _load_env() -> dict:
    """Read key=value pairs from .env (ignoring comments/blanks)."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _save_token(key: str, value: str):
    """Append or update a single key=value line in .env."""
    lines = []
    found = False
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith(f"{key}="):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line.rstrip())
    if not found:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  ✓ {key} → .env")


def build_auth_url(client_key: str, redirect_uri: str) -> str:
    """Build the TikTok authorization URL."""
    params = urllib.parse.urlencode({
        "client_key": client_key,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": "money_printer",
    })
    return f"{TIKTOK_AUTH_URL}?{params}"


def exchange_code(client_key: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for access + refresh token."""
    data = urllib.parse.urlencode({
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }).encode("utf-8")

    req = urllib.request.Request(TIKTOK_TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Cache-Control", "no-cache")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8"))
        print(f"  ✗ Token-Exchange fehlgeschlagen: HTTP {e.code}")
        print(f"    {json.dumps(body, indent=2)}")
        return {}

    if "error" in body and body.get("error"):
        print(f"  ✗ TikTok-Fehler: {body['error']}: {body.get('error_description', '')}")
        return {}

    return body.get("data", {})


def refresh_access_token(client_key: str, client_secret: str, refresh_token: str) -> dict:
    """Refresh an expired access token using the refresh token."""
    data = urllib.parse.urlencode({
        "client_key": client_key,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode("utf-8")

    req = urllib.request.Request(TIKTOK_TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Cache-Control", "no-cache")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8"))
        return {}

    if "error" in body and body.get("error"):
        return {}

    return body.get("data", {})


def main():
    parser = argparse.ArgumentParser(description="TikTok OAuth Setup")
    parser.add_argument("--code", help="Authorization code (non-interactive)")
    args = parser.parse_args()

    env = _load_env()
    client_key = env.get("TIKTOK_CLIENT_KEY", "")
    client_secret = env.get("TIKTOK_CLIENT_SECRET", "")
    redirect_uri = env.get("TIKTOK_REDIRECT_URI", "")

    if not client_key or not client_secret:
        print("ERROR: TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET fehlen in .env")
        sys.exit(1)

    # Check if tokens already exist
    if env.get("TIKTOK_ACCESS_TOKEN") and env.get("TIKTOK_REFRESH_TOKEN"):
        print("Tokens bereits vorhanden in .env.")
        print(f"  Access Token:  {env['TIKTOK_ACCESS_TOKEN'][:20]}...")
        print(f"  Refresh Token: {env['TIKTOK_REFRESH_TOKEN'][:20]}...")
        print("Erneut autorisieren? (j/n): ", end="", flush=True)
        if input().strip().lower() != "j":
            print("Abgebrochen.")
            return

    # Generate authorization URL
    auth_url = build_auth_url(client_key, redirect_uri)
    print()
    print("=" * 60)
    print("  TikTok OAuth — Money-Printer Pipeline")
    print("=" * 60)
    print()
    print("1. Öffne diese URL im Browser:")
    print()
    print(f"  {auth_url}")
    print()
    print("2. Logge dich ein und autorisiere die App.")
    print("3. Der Callback zeigt den Code auf der GitHub-Pages-Seite.")
    print("   Kopiere den Code aus der URL-Leiste (?code=...&state=...)")
    print()

    if args.code:
        code = args.code.strip()
        print(f"Code aus Argument: {code[:10]}...")
    else:
        print("Code einfügen: ", end="", flush=True)
        code = input().strip()

    if not code:
        print("Kein Code — abgebrochen.")
        sys.exit(1)

    # Exchange code for token
    print()
    print("Tausche Code gegen Token...")
    token_data = exchange_code(client_key, client_secret, code, redirect_uri)

    if not token_data:
        print("Token-Exchange fehlgeschlagen.")
        sys.exit(1)

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 0)
    refresh_expires_in = token_data.get("refresh_expires_in", 0)
    scope = token_data.get("scope", "")
    open_id = token_data.get("open_id", "")

    if not access_token or not refresh_token:
        print(f"Unerwartete Antwort: {json.dumps(token_data, indent=2)}")
        sys.exit(1)

    print()
    print("  ✓ Token erhalten!")
    print(f"    Open ID:        {open_id}")
    print(f"    Scope:          {scope}")
    print(f"    Access Token:   {access_token[:20]}... (läuft ab in {expires_in}s)")
    print(f"    Refresh Token:  {refresh_token[:20]}... (läuft ab in {refresh_expires_in}s)")
    print()

    # Save to .env
    _save_token("TIKTOK_OPEN_ID", open_id)
    _save_token("TIKTOK_ACCESS_TOKEN", access_token)
    _save_token("TIKTOK_REFRESH_TOKEN", refresh_token)
    _save_token("TIKTOK_SCOPE", scope)

    print()
    print("=" * 60)
    print("  ✓ OAuth abgeschlossen! Tokens in .env gespeichert.")
    print("  → tiktok_upload.py kann jetzt Videos hochladen.")
    print("=" * 60)


if __name__ == "__main__":
    main()
