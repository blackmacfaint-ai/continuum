# Money-Printer E2E — Ausführungs-Log (2026-08-23)

Stack-Check vor dem Lauf: ComfyUI 8188 → 200, Kokoro-DE 8881 → 200, Voicebox 17493 → 200.

## 1/3 `tts/speak` (Kokoro-DE, `martin`)

```bash
python scripts/tts_speak.py --text "Die Menschen, die dir am nächsten stehen, sind oft die, die du am meisten übersiehst." \
  --voice martin --engine kokoro --fallback-engine voicebox \
  --output C:/OmniRoute/ComfyUI/output/money_printer_e2e/voice.wav
```

```json
{"success": true, "audioPath": "C:\\OmniRoute\\ComfyUI\\output\\money_printer_e2e\\voice.wav", "engine": "kokoro", "duration": 4.367333}
```

> Fix unterwegs: Kokoro-Payload muss `{"model","voice","response_format":"wav","input"}` sein (nicht `text`/`mp3`);
> Voicebox braucht `profile_id` (Lookup per Profilname über `GET /profiles`) + `engine: qwen, model_size: 0.6B`,
> Antwortfeld `id`, Poll `/history/{id}` bis `completed`.

## 2/3 `video_generate` (Ken-Burns-Fallback)

```bash
python scripts/video_generate.py --base-image C:/OmniRoute/ComfyUI/output/user_test_360_00001_.png \
  --prompt "360 degree character showcase turn, drone b-roll style" --frames 6 --fps 24 --seed 177013 \
  --output C:/OmniRoute/ComfyUI/output/money_printer_e2e/broll.mp4
```

```json
{"success": true, "videoPath": "C:\\OmniRoute\\ComfyUI\\output\\money_printer_e2e\\broll.mp4", "frames": 6, "model": "ken-burns", "duration": 4.75}
```

ffprobe: 576×1024, 24fps, h264, 4.75s.

## 3/3 `artifacts/store`

```bash
python scripts/artifacts_store.py --artifact C:/OmniRoute/ComfyUI/output/money_printer_e2e/broll.mp4 --type video --tags e2e money-printer
```

```json
{"success": true, "artifactId": "7b06ffd94473", "path": "C:\\OmniRoute\\repos\\continuum\\data\\artifacts\\files\\video\\7b06ffd94473.mp4"}
```

Registry `data/artifacts/registry.json`: 1 Eintrag, Typ video, Tags [e2e, money-printer].

## Fazit

Die komplette Helper-Kette `tts/speak → video_generate → artifacts/store` läuft real durch.
Nächste offene Schritte: `ffmpeg_tiktok`-Step im E2E (Voice + B-Roll → 1080×1920 mit Untertiteln) und
echte Uploads (YouTube `config/client_secrets.json`, TikTok-API) — bewusst außerhalb dieses Meilensteins.
