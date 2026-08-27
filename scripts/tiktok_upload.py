#!/usr/bin/env python3
"""Money-Printer Step 8: TikTok Short-Upload via Content Posting API (Direct Post).

Nutzt den Refresh-Token aus .env, um automatisch einen frischen Access-Token
zu bekommen und das Video via push_by_file (Direct Post) auf TikTok zu publishen.

Usage:
  python scripts/tiktok_upload.py --video <tiktok.mp4> --topic "Hamburger Hafen"
  python scripts/tiktok_upload.py --video <tiktok.mp4> --topic "..." --privacy public
  python scripts/tiktok_upload.py --video <tiktok.mp4> --topic "..." --dry-run

Output: JSON {"success": true, "publish_id": ..., "video_id": ..., "url": ...} auf stdout.
Exit 0 = Erfolg, 1 = Upload fehlgeschlagen, 2 = kein Video/kein Token.
"""

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PROJECT_DIR = pathlib.Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_DIR / ".env"

TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
TIKTOK_VIDEO_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB chunks
MAX_POLL_ATTEMPTS = 60
POLL_INTERVAL = 5  # seconds


def _load_env() -> dict:
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


def refresh_access_token(client_key: str, client_secret: str, refresh_token: str) -> dict:
    """Refresh access token. Returns dict with access_token, refresh_token, open_id."""
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
        return {"error": f"HTTP {e.code}: {body.get('error', '')}"}

    if body.get("error"):
        return {"error": f"{body['error']}: {body.get('error_description', '')}"}

    return body.get("data", {})


def get_fresh_token(env: dict) -> str:
    """Get a fresh access token, refreshing if needed."""
    access_token = env.get("TIKTOK_ACCESS_TOKEN", "")
    refresh_token = env.get("TIKTOK_REFRESH_TOKEN", "")
    client_key = env.get("TIKTOK_CLIENT_KEY", "")
    client_secret = env.get("TIKTOK_CLIENT_SECRET", "")

    if not refresh_token:
        print("✗ Kein TIKTOK_REFRESH_TOKEN in .env — zuerst tiktok_oauth.py ausführen", file=sys.stderr)
        sys.exit(2)

    if not access_token:
        # No access token yet — need to do initial OAuth
        print("✗ Kein TIKTOK_ACCESS_TOKEN — zuerst tiktok_oauth.py ausführen", file=sys.stderr)
        sys.exit(2)

    # Try using existing access token first
    return access_token


def refresh_if_needed(client_key: str, client_secret: str, refresh_token: str) -> dict:
    """Refresh the token and save new tokens to .env."""
    result = refresh_access_token(client_key, client_secret, refresh_token)
    if "error" in result:
        return result

    new_access = result.get("access_token", "")
    new_refresh = result.get("refresh_token", "")

    if new_access:
        _save_token("TIKTOK_ACCESS_TOKEN", new_access)
    if new_refresh:
        _save_token("TIKTOK_REFRESH_TOKEN", new_refresh)

    return result


def query_creator_info(access_token: str) -> dict:
    """Query creator info — required before video upload."""
    req = urllib.request.Request(TIKTOK_CREATOR_INFO_URL, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/json; charset=UTF-8")
    req.data = b"{}"

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8"))
        return {"error": f"HTTP {e.code}: {json.dumps(body)}"}

    error = body.get("error", {})
    if error.get("code") and error["code"] != "ok":
        return {"error": f"Creator info: {error['code']}: {error.get('message', '')}"}

    return body.get("data", {})


def init_video_upload(access_token: str, video_size: int, title: str, privacy: str) -> dict:
    """Initialize video upload — get upload_url and publish_id."""
    chunk_count = max(1, (video_size + CHUNK_SIZE - 1) // CHUNK_SIZE)

    payload = json.dumps({
        "post_info": {
            "title": title,
            "privacy_level": privacy,
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": CHUNK_SIZE,
            "total_chunk_count": chunk_count,
        }
    }).encode("utf-8")

    req = urllib.request.Request(TIKTOK_VIDEO_INIT_URL, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/json; charset=UTF-8")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8"))
        return {"error": f"HTTP {e.code}: {json.dumps(body)}"}

    error = body.get("error", {})
    if error.get("code") and error["code"] != "ok":
        return {"error": f"Video init: {error['code']}: {error.get('message', '')}"}

    return body.get("data", {})


def upload_video_chunks(upload_url: str, video_path: pathlib.Path, video_size: int) -> bool:
    """Upload video in chunks to TikTok's upload endpoint."""
    offset = 0
    with open(video_path, "rb") as f:
        while offset < video_size:
            chunk_end = min(offset + CHUNK_SIZE - 1, video_size - 1)
            chunk = f.read(CHUNK_SIZE)

            content_range = f"bytes {offset}-{chunk_end}/{video_size}"
            req = urllib.request.Request(upload_url, data=chunk, method="PUT")
            req.add_header("Content-Range", content_range)
            req.add_header("Content-Type", "video/mp4")

            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    resp_code = resp.getcode()
                    if resp_code not in (200, 201, 206):
                        print(f"  ✗ Chunk upload failed: HTTP {resp_code}", file=sys.stderr)
                        return False
            except urllib.error.HTTPError as e:
                print(f"  ✗ Chunk upload error: HTTP {e.code}", file=sys.stderr)
                return False

            offset += CHUNK_SIZE
            pct = min(100, int(offset / video_size * 100))
            print(f"  ⏳ {pct}% ({offset}/{video_size} bytes)")

    return True


def poll_publish_status(access_token: str, publish_id: str) -> dict:
    """Poll the publish status until complete or failed."""
    payload = json.dumps({"publish_id": publish_id}).encode("utf-8")

    for attempt in range(MAX_POLL_ATTEMPTS):
        req = urllib.request.Request(TIKTOK_STATUS_URL, data=payload, method="POST")
        req.add_header("Authorization", f"Bearer {access_token}")
        req.add_header("Content-Type", "application/json; charset=UTF-8")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode("utf-8"))
            time.sleep(POLL_INTERVAL)
            continue

        error = body.get("error", {})
        if error.get("code") and error["code"] != "ok":
            time.sleep(POLL_INTERVAL)
            continue

        status = body.get("data", {})
        status_code = status.get("status", "")
        video_id = status.get("video", {}).get("video_id", "")

        if status_code == "SUCCESS":
            return {"success": True, "video_id": video_id, "publish_id": publish_id}
        elif status_code in ("FAILED", "CANCELLED"):
            return {"success": False, "error": f"Status: {status_code}", "status": status}
        else:
            # Still processing
            time.sleep(POLL_INTERVAL)

    return {"success": False, "error": f"Timeout after {MAX_POLL_ATTEMPTS * POLL_INTERVAL}s"}


def main():
    parser = argparse.ArgumentParser(description="TikTok Direct Post Upload")
    parser.add_argument("--video", required=True, help="Path to video file")
    parser.add_argument("--topic", default="", help="Video title/topic")
    parser.add_argument("--privacy", default="PUBLIC_TO_EVERYONE",
                       choices=["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"])
    parser.add_argument("--tags", default="", help="Hashtags (space-separated)")
    parser.add_argument("--dry-run", action="store_true", help="Validate without uploading")
    args = parser.parse_args()

    video_path = pathlib.Path(args.video)
    if not video_path.exists():
        print(json.dumps({"success": False, "error": f"Video not found: {args.video}"}))
        sys.exit(2)

    video_size = video_path.stat().st_size

    # Build title with hashtags
    title = args.topic.strip() if args.topic else video_path.stem
    if args.tags:
        tags = args.tags.strip().split()
        tag_str = " ".join(f"#{t.lstrip('#')}" for t in tags)
        title = f"{title} {tag_str}"

    env = _load_env()
    client_key = env.get("TIKTOK_CLIENT_KEY", "")
    client_secret = env.get("TIKTOK_CLIENT_SECRET", "")
    refresh_token = env.get("TIKTOK_REFRESH_TOKEN", "")

    if not client_key or not client_secret:
        print(json.dumps({"success": False, "error": "No TikTok credentials in .env"}))
        sys.exit(2)

    if not refresh_token:
        print(json.dumps({"success": False, "error": "No refresh token — run tiktok_oauth.py first"}))
        sys.exit(2)

    if args.dry_run:
        print(json.dumps({
            "success": True,
            "dry_run": True,
            "title": title,
            "privacy": args.privacy,
            "video": str(video_path),
            "video_size": video_size,
        }))
        sys.exit(0)

    # Step 1: Get fresh access token
    print("TikTok Upload: Token refresh...")
    token_result = refresh_if_needed(client_key, client_secret, refresh_token)
    if "error" in token_result:
        print(json.dumps({"success": False, "error": f"Token refresh: {token_result['error']}"}))
        sys.exit(1)

    access_token = token_result.get("access_token", env.get("TIKTOK_ACCESS_TOKEN", ""))
    print(f"  ✓ Token refreshed (expires in {token_result.get('expires_in', '?')}s)")

    # Step 2: Query creator info (required by TikTok)
    print("TikTok Upload: Creator info...")
    creator = query_creator_info(access_token)
    if "error" in creator:
        # Token might be stale — try refresh
        print(f"  ⚠ Creator info failed ({creator['error']}), refreshing token...")
        token_result = refresh_if_needed(client_key, client_secret, env.get("TIKTOK_REFRESH_TOKEN", ""))
        if "error" in token_result:
            print(json.dumps({"success": False, "error": f"Token refresh retry: {token_result['error']}"}))
            sys.exit(1)
        access_token = token_result.get("access_token", access_token)
        creator = query_creator_info(access_token)
        if "error" in creator:
            print(json.dumps({"success": False, "error": f"Creator info: {creator['error']}"}))
            sys.exit(1)

    username = creator.get("creator_username", "unknown")
    nickname = creator.get("creator_nickname", username)
    print(f"  ✓ Creator: @{username} ({nickname})")

    # Step 3: Initialize video upload
    print(f"TikTok Upload: Init ({video_size} bytes, {max(1, (video_size + CHUNK_SIZE - 1) // CHUNK_SIZE)} chunks)...")
    init = init_video_upload(access_token, video_size, title, args.privacy)
    if "error" in init:
        print(json.dumps({"success": False, "error": f"Video init: {init['error']}"}))
        sys.exit(1)

    publish_id = init.get("publish_id", "")
    upload_url = init.get("upload_url", "")
    print(f"  ✓ publish_id: {publish_id}")

    # Step 4: Upload video chunks
    print("TikTok Upload: Uploading...")
    if not upload_video_chunks(upload_url, video_path, video_size):
        print(json.dumps({"success": False, "error": "Chunk upload failed", "publish_id": publish_id}))
        sys.exit(1)

    print("  ✓ Upload complete, waiting for processing...")

    # Step 5: Poll publish status
    result = poll_publish_status(access_token, publish_id)
    if result.get("success"):
        video_id = result.get("video_id", "")
        url = f"https://www.tiktok.com/@{username}/video/{video_id}" if video_id else ""
        output = {
            "success": True,
            "publish_id": publish_id,
            "video_id": video_id,
            "url": url,
            "username": username,
            "title": title,
        }
        print(json.dumps(output))
        # Save result
        result_file = PROJECT_DIR / "data" / "audio" / "tiktok.json"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(f"  ✓ Ergebnis → {result_file}")
    else:
        print(json.dumps({"success": False, "error": result.get("error", "Unknown"), "publish_id": publish_id}))
        sys.exit(1)


if __name__ == "__main__":
    main()
