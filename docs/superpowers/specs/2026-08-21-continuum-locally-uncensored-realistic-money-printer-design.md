# Continuum + Locally Uncensored Realistic Money Printer — Design

**Date:** 2026-08-21
**Status:** Approved (4/4 sections)
**Repo:** `C:\OmniRoute\repos\continuum` (AGPL-3.0, CambrianTech)
**Replaces:** `C:\OmniRoute\repos\mark-l` (archived to `mark-l.archive/`)
**Hardware:** AMD RX 6800 XT 16GB, 32GB RAM, 12 Cores, DirectML

## 1. Overview

Continuum Grid wird Hauptprozess (Docker Model Runner, Rust core, 26 Module, 1,179+ tests). Mark-L HUD wird stillgelegt. Realistische Bild/Video-Generierung aus **Locally Uncensored** (`C:\Program Files\Locally Uncensored` — Electron + `llama-server.exe` 56MB + `whisper_server.py` faster-whisper) wird nicht via Electron-API proxied, sondern direkt via **ComfyUI** (`localhost:8188`, `comfyui-venv` Python 3.12, `av` 18.1, `faster-whisper` 1.2.1) mit Checkpoint `realisticVisionV60B1_v51HyperVAE.safetensors` (1.99GB, SD1.5, HyperVAE) plus erweiterten Civitai-Modellen für faceless TikTok/YouTube Money Printer.

Ziel: `Money Printer` Pipeline faceless generieren → passives Einkommen via `youtube-upload` / `tiktok-video-producer` (bereits in `orca/` verifiziert: 498s E2E `tiktok.mp4` 1080x1920).

## 2. Architecture

```
Continuum Grid (Hauptprozess, Docker, Rust core, TS bridge)
 ├─ continuum-core (Rust) — Commands.execute(), Events.subscribe(), 320 auto-discovered commands
 ├─ Recipes: realistic-image, realistic-video, money-printer-realistic
 │   pipeline: rag/build → ai/should-respond → image/generate-realistic → artifacts/store → youtube/upload
 ├─ Command image/generate-realistic (src/commands/image/generate-realistic.ts)
 │   → HTTP POST host.docker.internal:8188/prompt (ComfyUI)
 └─ ComfyUI (host, comfyui-venv, 8188, Q4_K_M via ComfyUI-GGUF)
     └─ Checkpoints/models → PNG/MP4 → continuum artifacts/ → Grid

Ollama 11434 — Qwen3.5-9B-DeepSeek-V4-Flash-GGUF:Q4_K_M (8.95B, 262k ctx, Q4_K_M, 6.6GB, hf.co/Jackrong)
 └─ Haupt-LLM (llm_provider ollama, llm_url http://localhost:11434, keep_alive -1, num_predict 500)
    vorher auto/best-chat (oc/hy3-free) → 401 DeepSeek-Free abgelaufen, oc/big-pickle 429
    fix: core/llm_client.py num_gpu 99 entfernt, local_session.py arguments als dict für Ollama

ComfyUI host: C:\OmniRoute\ComfyUI (oder C:\OmniRoute\repos\mark-l\ComfyUI fallback)
Voice: Kokoro-DE 8881 martin (Echtzeit) + Voicebox 17493 Overlay DE (vorbereitet, qwen-tts-0.6B)
```

Mark-L Archiv: `mark-l.archive/` Tag `pre-continuum`, `start-all.cmd`/`MARK L.lnk` deaktiviert, `long_term.json` → Continuum L3 Engrams.

## 3. Components

### 3.1 Checkpoint-Setup
- Quelle: `C:\Users\Sebastian\Downloads\realisticVisionV60B1_v51HyperVAE.safetensors` → Ziel `C:\OmniRoute\ComfyUI\models\checkpoints\realisticVisionV60B1_v51HyperVAE.safetensors` (sha256 verifizieren, 1.99GB). Fallback prüfen: `C:\OmniRoute\repos\mark-l\ComfyUI\models\checkpoints\`.
- ComfyUI Start: `ui/run-comfyui.cmd` via `comfyui-venv` (Python 3.12, bereits 576x1024 verifiziert).
- Custom Nodes: `ComfyUI/custom_nodes/ComfyUI-GGUF` (`git clone https://github.com/city96/ComfyUI-GGUF`), `auto_convert` Tools für GGUF-Quantisierung.

### 3.2 Command image/generate-realistic.ts
- Eingaben: `prompt` (string), `negativePrompt` (string, default "bad anatomy, blurry"), `width` (512-1024, default 576), `height` (768-1024), `steps` (20-30, default 25), `cfg` (7), `seed` (int), `batchSize` (1-4), `checkpoint` (enum).
- Workflow: `CheckpointLoaderSimple` (realisticVision) → `CLIPTextEncode` (prompt/negative) → `KSampler` (euler, 25, cfg 7) → `VAEDecode` (HyperVAE integriert) → `SaveImage` (prefix `continuum-realistic`). Für FLUX: `UNETLoader` + `CLIPLoader` (clip_l, t5xxl) + `VAELoader` (ae).
- Host-Auflösung: `host.docker.internal:8188` wenn in Docker, sonst `localhost:8188` (probe `GET /system_stats`).
- Output: `artifacts/` PNG Pfad, Metadaten `seed`, `checkpoint`, `prompt` → RAG L1.

### 3.3 Recipes
- `realistic-image`: Pipeline `rag/build (maxMessages 20) → ai/should-respond (human-focused) → image/generate-realistic → artifacts/store`. Tags `realistic, image, money-printer`.
- `realistic-video`: Erweitert via `minimax-h3` (Civitai 2830065 int8/int4 + flat-2 VR workflow 33927) oder `zImageTurbo` (1353314). 6 Frames sequenziell → `ffmpeg` 24fps 720p. Falls AnimateDiff nicht vorhanden, Fallback: 6x `realistic-image` + Ken-Burns.
- `money-printer-realistic`: `ai/generate` (Qwen GGUF, 150 Wörter deutsch) → `tts/speak` (Kokoro/Voicebox) → `image/generate-realistic` (batch 3) → `video/generate` (optional B-Roll) → `ffmpeg_tiktok` (1080x1920, subtitles via `faster-whisper small`) → `artifacts/store` → `youtube/upload`.

### 3.4 Forge-Alloy Option C (später)
- Wenn A stabil, `continuum-ai/realistic-vision-lora` trainieren: Datensatz = erfolgreiche `money-printer-realistic` Artifacts (Academy Continuous Experiential, sentinel-scored), Contract `forge-alloy` (ES256, SHA-256, Benchmark HumanEval + CLIP-Score), Publish HuggingFace `continuum:*` Tags, Genome Paging `genome.activateSkill('realistic-vision')`.

## 4. Model Matrix

| Modell | Quelle | Typ | VRAM | Nutzen | Pfad |
|---|---|---|---|---|---|
| realisticVisionV60B1_v51HyperVAE.safetensors | Downloads/ (501240) | SD1.5 + HyperVAE | 4GB | Basis realistisch, 576x1024, euler 25 | `models/checkpoints/` |
| flux1DevAsian (672618) | Civitai FLUX.1 dev | DiT | 12GB → 6GB GGUF | Asiatische Realistik, FLUX Quickstart (flux1-dev + ae + clip_l + t5xxl) | `models/diffusion_models/` + `models/vae/` + `models/clip/` |
| ComfyUI-GGUF auto_convert | github.com/city96/ComfyUI-GGUF | Quantizer | — | GGUF Q4_K_M für RX 6800 XT | `custom_nodes/ComfyUI-GGUF` |
| zImageTurbo (1353314) | Civitai Stable Yogi | SDXL Turbo | 6GB | 4-Step Thumbnails/Shorts | `models/checkpoints/` |
| minimax-h3 (2830065 int8/int4, 33927 flat-2) | Civitai | Video DiT | 10GB → 6GB int4 | 720p 6s VR Clips, B-Roll | `models/minimax/` |

Alle Civitai Downloads: `C:\OmniRoute\ComfyUI\models\` + SHA256 Checksum, Fallback HF Mirror, Cache 20GB.

## 5. Data Flow

```
[Grid] Persona Chat (positron widget, Lit Shadow DOM)
  → Recipe money-printer-realistic
    1. rag/build (20 msgs, L1 working set)
    2. ai/should-respond (energy-aware, 3s-10s cadence)
    3. ai/generate (Qwen3.5-9B GGUF, temp 0.6, top_p 0.95, 262k ctx)
       → Skript de
    4. tts/speak → WAV (Kokoro 8881 / Voicebox 17493)
    5. image/generate-realistic (ComfyUI POST /prompt, poll /history, GET /view)
       → PNG 576x1024
    6. video/generate (Minimax H3, optional)
       → MP4 720p
    7. ffmpeg_tiktok (libx264, aac, subtitles srt_from_audio)
       → 1080x1920 9:16
    8. artifacts/store (type-safe ORM, Postgres+SQLite)
    9. youtube/upload (resumable) / schedule_post
```

Loops: `Continuous Experiential` → erfolgreiche Artifacts → L3 Engrams → L4 LoRA (später).

## 6. Error Handling

- ComfyUI down (8188): `onError: retry` 3x (5s backoff), dann `voice-only` Fallback (WAV + Stock BG `assets/bg-tasks`), Log `continuum-core` + `Events.subscribe("image/failed")`.
- VRAM OOM: `ComfyUI-GGUF` erzwingen, sequenziell (FLUX → Minimax nicht parallel), `auto-unload` nach jedem Batch, Monitor `gpu/stats` (NVIDIA + Apple Silicon).
- Civitai 429/403: lokaler Cache + HF Mirror, `User-Agent` Header, `curl --retry 3`.
- Ollama 400: bereits gefixt (num_gpu entfernt, arguments dict für Ollama, string für OpenAI), `ensure_ollama_running` + `ollama serve` Restart.
- STT Ellipsis: `core/stt.py` `…`→`...` (cp1252).
- PowerShell 2>nul: `start-all.cmd` jetzt Python `requests` HealthChecks.

## 7. Testing

- Unit: `src/commands/image/generate-realistic.test.ts` (mock ComfyUI `POST /prompt` → 200, `GET /history` → completed, `GET /view` → PNG).
- Recipe: `recipes/realistic-image.test.ts` (RAG build → image → artifacts, 1.99GB checkpoint vorhanden, `ffprobe` 1080x1920).
- E2E Money Printer: `money-printer-realistic` dry-run `batchSize=1` → `artifacts/list` → `youtube/upload` mock, 30s Video via `orca/media.py` Pfad (576x1024, 25 steps, seed 100).
- Manual: `curl http://localhost:8188/system_stats`, `ollama list` (hf.co/Jackrong...), `voicebox` 17493 profiles.
- Continuum Setup: `./setup.sh` (WSL2+Docker) oder `install.ps1` (winget), DMR GPU toggles, `bootstrap.sh` inside WSL.

## 8. Migration & Ops

- Archiv: `git mv mark-l mark-l.archive && git tag pre-continuum`.
- Config: `config/api_keys.json` (llm_provider ollama, llm_url 11434, llm_model hf.co/Jackrong..., stt whisper small/de, tts kokoro/voicebox) → Continuum `continuum-core` env `OLLAMA_HOST`, `COMFYUI_URL`.
- Autostart: `start-all.cmd` erweitert um `continuum` (`docker compose up` + `ollama serve` + `comfyui`), `Startup/MARK L.lnk` → `Startup/Continuum.lnk`.
- Ports: 8188 ComfyUI, 11434 Ollama, 17493 Voicebox, 20128 OmniRoute (optional fallback), 8000 Mark-L Dashboard (deprecated).

## 9. Future (Option C)

Adapter `realistic-vision-lora` ($0.10-8) → HuggingFace `continuum-ai`, Genome Paging, Breeding über mehrere Eltern, Selection via `continuum-core` Benchmarks (HumanEval + CLIP-Score).

---

**Approval:** 2026-08-21 — 4/4 sections approved (A mit Option C, ComfyUI direkt, Recipe, Modell-Matrix erweitert).
**Next:** `writing-plans` skill → `docs/superpowers/plans/YYYY-MM-DD-...-plan.md` (phasenweise: 1. Checkpoint+ComfyUI-GGUF, 2. Command+Recipe, 3. Money-Printer, 4. Forge LoRA).
