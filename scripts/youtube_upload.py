#!/usr/bin/env python3
"""
YouTube Upload Helper for continuum money-printer-realistic
Resumable upload via YouTube Data API v3 with 3x retry, as per recipe strategy.

Usage:
  python scripts/youtube_upload.py --file C:/OmniRoute/ComfyUI/output/money_printer_v2/tiktok.mp4 --title "Gemuetliches Cafe" --privacy unlisted
  python scripts/youtube_upload.py --file <video> --title "Title" --description "Desc" --privacy public --category 22

Requires:
  pip install google-api-python-client google-auth-oauthlib google-auth
  config/client_secrets.json (OAuth 2.0 Client ID from Google Cloud Console)

Setup Google Cloud (see Kanban GOOGLE-CLOUD-YOUTUBE):
  1. https://console.cloud.google.com/apis/credentials -> Create OAuth Client ID (Desktop App) -> Download client_secrets.json -> place at config/client_secrets.json
  2. Enable YouTube Data API v3 in your project
  3. First run will open browser for OAuth consent and save token at config/youtube_token.json

On missing credentials, exits with code 2 (stub skip signal for continuum youtube/upload onError:skip).
"""
import argparse
import json
import pathlib
import sys
import time

DEFAULT_CLIENT_SECRETS = pathlib.Path(__file__).parent.parent / "config" / "client_secrets.json"
TOKEN_PATH = pathlib.Path(__file__).parent.parent / "config" / "youtube_token.json"

def find_client_secrets(custom: str | None) -> pathlib.Path | None:
    candidates = [
        pathlib.Path(custom) if custom else None,
        pathlib.Path("config/client_secrets.json"),
        pathlib.Path("C:/OmniRoute/repos/continuum/config/client_secrets.json"),
        DEFAULT_CLIENT_SECRETS,
        pathlib.Path.cwd() / "config" / "client_secrets.json",
    ]
    for p in candidates:
        if p and p.exists() and p.is_file():
            try:
                json.loads(p.read_text(encoding="utf-8"))
                return p
            except Exception:
                continue
    env = pathlib.Path(__import__("os").environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")) if __import__("os").environ.get("GOOGLE_APPLICATION_CREDENTIALS") else None
    if env and env.exists():
        return env
    return None

def parse_args():
    ap = argparse.ArgumentParser(description="Upload video to YouTube (resumable, 3x retry)")
    ap.add_argument("--file", required=True, help="Path to video file (e.g. tiktok.mp4)")
    ap.add_argument("--title", required=True, help="Video title (max 100 chars)")
    ap.add_argument("--description", default="", help="Video description")
    ap.add_argument("--privacy", choices=["public", "private", "unlisted"], default="public", help="Privacy status")
    ap.add_argument("--category", default="22", help="YouTube categoryId (22=People & Blogs, 24=Entertainment)")
    ap.add_argument("--tags", nargs="*", default=["faceless", "tiktok", "realistic", "money-printer"], help="Tags")
    ap.add_argument("--client-secrets", default=None, help="Path to client_secrets.json")
    ap.add_argument("--dry-run", action="store_true", help="Validate args without uploading")
    return ap.parse_args()

def main():
    args = parse_args()
    video_path = pathlib.Path(args.file)
    if not video_path.exists():
        print(f"ERROR: video not found: {video_path}", file=sys.stderr)
        sys.exit(1)
    if video_path.stat().st_size < 1000:
        print(f"ERROR: video too small: {video_path.stat().st_size} bytes", file=sys.stderr)
        sys.exit(1)

    secrets = find_client_secrets(args.client_secrets)
    if not secrets:
        print("SKIP: client_secrets.json not found", file=sys.stderr)
        print("Place OAuth Client JSON at config/client_secrets.json", file=sys.stderr)
        print("See Kanban GOOGLE-CLOUD-YOUTUBE for setup steps", file=sys.stderr)
        print(f"Would upload: {video_path} title={args.title!r} privacy={args.privacy}", file=sys.stderr)
        sys.exit(2)

    if args.dry_run:
        print(f"DRY-RUN OK: {video_path} ({video_path.stat().st_size} bytes) title={args.title!r} secrets={secrets}")
        sys.exit(0)

    # Real upload
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("ERROR: missing google-api-python-client. Install: pip install google-api-python-client google-auth-oauthlib google-auth", file=sys.stderr)
        sys.exit(1)

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        print(f"Token saved to {TOKEN_PATH}")

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": args.title[:100],
            "description": args.description[:5000],
            "tags": args.tags[:15],
            "categoryId": args.category,
        },
        "status": {
            "privacyStatus": args.privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize= -1, resumable=True, mimetype="video/mp4")

    # 3x retry as per recipe strategy
    for attempt in range(1, 4):
        try:
            print(f"Upload attempt {attempt}/3: {video_path.name} -> {args.title!r}")
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"  progress {int(status.progress()*100)}%")
            video_id = response.get("id")
            url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"SUCCESS: {url}")
            print(json.dumps(response, indent=2))
            sys.exit(0)
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}", file=sys.stderr)
            if attempt == 3:
                sys.exit(1)
            time.sleep(2 ** attempt)

if __name__ == "__main__":
    main()
