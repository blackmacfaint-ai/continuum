# Kanban: GOOGLE-CLOUD-YOUTUBE

**ID:** a1b2c3d4e5
**Spalte:** todo
**Titel:** P2: YouTube Google Cloud Integration für continuum youtube/upload (GOOGLE-CLOUD-YOUTUBE)

**Notiz:**
Helper scripts/youtube_upload.py + Stub src/commands/youtube/upload ist fertig (SKIP wenn kein credentials). Für echten Upload: 1) https://console.cloud.google.com/apis/credentials -> OAuth Client ID (Desktop App) -> Download client_secrets.json -> nach C:/OmniRoute/repos/continuum/config/client_secrets.json legen. 2) YouTube Data API v3 im Projekt aktivieren. 3) pip install google-api-python-client google-auth-oauthlib google-auth. 4) python scripts/youtube_upload.py --file C:/OmniRoute/ComfyUI/output/money_printer_v2/tiktok.mp4 --title 'Gemuetliches Cafe' --privacy unlisted --dry-run testen, dann ohne --dry-run echte Upload (resumable 3x retry). Betrifft Recipe money-printer-realistic youtube/upload onError:skip. Artefakt bereit: money_printer_v2/tiktok.mp4 1080x1920 11.73s.

**Helper:** `scripts/youtube_upload.py`
**Stub:** `src/commands/youtube/upload/shared/YoutubeUploadTypes.ts`
**Artefakt:** `C:/OmniRoute/ComfyUI/output/money_printer_v2/tiktok.mp4`
**Recipe:** `src/system/recipes/money-printer-realistic.json` `youtube/upload`

**Erstellt:** 2026-08-22T20:01:48.701073+00:00
