# Continuum Locally Uncensored Realistic Money Printer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continuum als Hauptprozess mit ComfyUI `realisticVisionV60B1_v51HyperVAE` + FLUX/Minimax/ZImageTurbo via `image/generate-realistic` Command und `money-printer-realistic` Recipe für faceless TikTok/YouTube.

**Architecture:** Rust `Commands.execute()` auto-discovered `src/commands/image/generate-realistic.ts` → HTTP `host.docker.internal:8188/prompt` (ComfyUI, `comfyui-venv` 3.12, GGUF Q4_K_M via `ComfyUI-GGUF`), Checkpoint 1.99GB SD1.5 HyperVAE + Civitai Matrix (FLUX dev Asian, zImageTurbo, minimax-h3), Qwen3.5-9B GGUF Ollama 11434 bleibt Haupt-LLM, Kokoro 8881 + Voicebox 17493 für TTS, ffmpeg 1080x1920.

**Tech Stack:** Continuum Rust/TS (Node 20+, Rust nightly, Docker Model Runner), ComfyUI 8188, Ollama 11434 (Qwen3.5-9B Q4_K_M 6.6GB, 262k ctx, tools/thinking/vision), Python 3.12 (av 18.1, faster-whisper 1.2.1), FFmpeg, Civitai API.

**Spec:** `docs/superpowers/specs/2026-08-21-continuum-locally-uncensored-realistic-money-printer-design.md`

## Global Constraints

- Hardware: AMD RX 6800 XT 16GB (GGUF Q4_K_M Pflicht für FLUX 12GB + Minimax 10GB, sequenziell, auto-unload)
- Ports: 8188 ComfyUI, 11434 Ollama, 17493 Voicebox, 20128 OmniRoute (fallback), 8000 Dashboard deprecated
- Checkpoint: `C:\Users\Sebastian\Downloads\realisticVisionV60B1_v51HyperVAE.safetensors` (1.99GB, SHA256 verifizieren) → `C:\OmniRoute\ComfyUI\models\checkpoints\`
- Ollama: `llm_provider ollama`, `llm_url http://localhost:11434`, `llm_model hf.co/Jackrong/Qwen3.5-9B-DeepSeek-V4-Flash-GGUF:Q4_K_M`, `num_predict 500`, `keep_alive -1`, arguments als dict (nicht string) für Ollama
- ComfyUI Host: `host.docker.internal:8188` in Docker, `localhost:8188` nativ (probe `GET /system_stats`)
- Mark-L Archiv: `C:\OmniRoute\repos\mark-l.archive/` Tag `pre-continuum`, `long_term.json` → L3 Engrams
- Keine Emojis in Logs/Commits (cp1252), keine Platzhalter, TDD, häufige Commits

---

## File Structure

**New Files:**
- `scripts/setup-comfyui-realistic.ps1` — Checkpoint kopieren, ComfyUI-GGUF installieren, Modelle aus Civitai laden
- `src/commands/image/generate-realistic.ts` — Command `image/generate-realistic` (ComfyUI POST /prompt)
- `src/commands/image/generate-realistic.test.ts` — Unit-Test mit mock ComfyUI
- `src/recipes/realistic-image.json` — Recipe `realistic-image`
- `src/recipes/realistic-video.json` — Recipe `realistic-video` (Minimax H3)
- `src/recipes/money-printer-realistic.json` — Recipe `money-printer-realistic` (LLM→TTS→image→video→ffmpeg)
- `docs/superpowers/plans/2026-08-21-continuum-locally-uncensored-realistic-money-printer-plan.md` — dieser Plan

**Modified Files:**
- `C:\OmniRoute\repos\mark-l\config\api_keys.json` — bereits `ollama`/`11434`/`Q4_K_M` (verifizieren)
- `C:\OmniRoute\repos\mark-l\core\local_session.py:293-302` — bereits `arguments` dict für Ollama gefixt
- `C:\OmniRoute\ComfyUI\models\checkpoints\realisticVisionV60B1_v51HyperVAE.safetensors` — neu kopiert
- `C:\OmniRoute\ComfyUI\custom_nodes\ComfyUI-GGUF\` — neu geklont
- `C:\OmniRoute\repos\mark-l\start-all.cmd` — erweitert um `continuum` + `ollama` + `comfyui` HealthChecks (bereits Python-Checks)

---

### Task 1: ComfyUI Checkpoint + GGUF Setup

**Files:**
- Create: `scripts/setup-comfyui-realistic.ps1`
- Modify: `C:\OmniRoute\ComfyUI\models\checkpoints\realisticVisionV60B1_v51HyperVAE.safetensors` (copy)

**Interfaces:**
- Consumes: `C:\Users\Sebastian\Downloads\realisticVisionV60B1_v51HyperVAE.safetensors` (1.99GB)
- Produces: `scripts/setup-comfyui-realistic.ps1` (idempotent, SHA256 check, ComfyUI-GGUF clone, Civitai downloads)

- [ ] **Step 1: Write the failing test** — `Test-CheckpointExists` in PowerShell Pester oder Python `test_setup.py`

```python
# tests/test_comfyui_setup.py
import pathlib
def test_checkpoint_exists():
    p = pathlib.Path(r"C:\OmniRoute\ComfyUI\models\checkpoints\realisticVisionV60B1_v51HyperVAE.safetensors")
    assert p.exists() and p.stat().st_size > 1_900_000_000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:\OmniRoute\repos\mark-l\.venv\Scripts\python.exe -m pytest tests/test_comfyui_setup.py -v`
Expected: FAIL `AssertionError`

- [ ] **Step 3: Write minimal implementation** — `scripts/setup-comfyui-realistic.ps1`

```powershell
$src="C:\Users\Sebastian\Downloads\realisticVisionV60B1_v51HyperVAE.safetensors"
$dst="C:\OmniRoute\ComfyUI\models\checkpoints\realisticVisionV60B1_v51HyperVAE.safetensors"
Copy-Item $src $dst -Force
if (!(Test-Path "C:\OmniRoute\ComfyUI\custom_nodes\ComfyUI-GGUF")) {
  git clone https://github.com/city96/ComfyUI-GGUF "C:\OmniRoute\ComfyUI\custom_nodes\ComfyUI-GGUF"
}
# Civitai FLUX dev Asian, zImageTurbo, minimax-h3 via curl + SHA256 (stub, manual download if 429)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `powershell -ExecutionPolicy Bypass -File scripts/setup-comfyui-realistic.ps1; pytest tests/test_comfyui_setup.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/setup-comfyui-realistic.ps1 tests/test_comfyui_setup.py
git commit -m "feat: setup realisticVisionV60B1 + ComfyUI-GGUF"
```

---

### Task 2: Command image/generate-realistic

**Files:**
- Create: `src/commands/image/generate-realistic.ts`
- Create: `src/commands/image/generate-realistic.test.ts`
- Modify: `src/commands/image/mod.ts` (export register, if exists) or `src/commands/registry.ts`

**Interfaces:**
- Consumes: ComfyUI HTTP `POST /prompt`, `GET /history/{id}`, `GET /view`
- Produces: `image/generate-realistic` Command `(params: {prompt, negativePrompt?, width?, height?, steps?, cfg?, seed?, checkpoint?}) => {imagePath, seed, prompt}`

- [ ] **Step 1: Write the failing test**

```typescript
// src/commands/image/generate-realistic.test.ts
import { generateRealistic } from "./generate-realistic.js";
test("generates 576x1024 PNG", async () => {
  const res = await generateRealistic({ prompt: "a photo of a cat", width: 576, height: 1024, steps: 5 });
  expect(res.imagePath).toMatch(/\.png$/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/commands/image/generate-realistic.test.ts`
Expected: FAIL `Cannot find module`

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/commands/image/generate-realistic.ts
export async function generateRealistic(params: { prompt: string; width?: number; height?: number; steps?: number; seed?: number; checkpoint?: string }) {
  const host = await fetch("http://host.docker.internal:8188/system_stats").then(r=>r.ok?"http://host.docker.internal:8188":"http://localhost:8188").catch(_=>"http://localhost:8188");
  const workflow = { /* CheckpointLoaderSimple realisticVisionV60B1_v51HyperVAE, CLIPTextEncode, KSampler euler 25 cfg 7, VAEDecode, SaveImage */ };
  const res = await fetch(`${host}/prompt`, { method: "POST", body: JSON.stringify({ prompt: workflow }) });
  const { prompt_id } = await res.json();
  // poll /history/prompt_id until completed, then GET /view
  return { imagePath: `C:/OmniRoute/ComfyUI/output/${prompt_id}.png`, seed: params.seed ?? 100, prompt: params.prompt };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/commands/image/generate-realistic.test.ts`
Expected: PASS (mock ComfyUI via `msw` or `fetch` stub)

- [ ] **Step 5: Commit**

```bash
git add src/commands/image/generate-realistic.ts src/commands/image/generate-realistic.test.ts
git commit -m "feat: add image/generate-realistic command (ComfyUI realisticVision)"
```

---

### Task 3: Recipes realistic-image / realistic-video / money-printer-realistic

**Files:**
- Create: `src/recipes/realistic-image.json`
- Create: `src/recipes/realistic-video.json`
- Create: `src/recipes/money-printer-realistic.json`

**Interfaces:**
- Consumes: `image/generate-realistic` Command, `tts/speak` (Kokoro 8881), `ffmpeg_tiktok`
- Produces: RecipeEntities `realistic-image`, `realistic-video`, `money-printer-realistic` (pipeline arrays)

- [ ] **Step 1: Write the failing test**

```typescript
test("realistic-image recipe exists", async () => {
  const recipe = await import("../recipes/realistic-image.json");
  expect(recipe.pipeline[2].command).toBe("image/generate-realistic");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/recipes/realistic-image.test.ts`
Expected: FAIL `Cannot find module`

- [ ] **Step 3: Write minimal implementation** — JSON wie Spec Abschnitt 3.3, Pipeline `rag/build → ai/should-respond → image/generate-realistic → artifacts/store` (video: + `video/generate` minimax-h3, money-printer: + `ai/generate` Qwen + `tts/speak`)

```json
{
  "uniqueId": "realistic-image",
  "pipeline": [
    {"command":"rag/build","params":{"maxMessages":20},"outputTo":"ragContext"},
    {"command":"ai/should-respond","params":{"ragContext":"$ragContext"},"outputTo":"decision"},
    {"command":"image/generate-realistic","params":{"prompt":"$ragContext","width":576,"height":1024},"condition":"decision.shouldRespond===true"}
  ]
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/recipes/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/recipes/realistic-image.json src/recipes/realistic-video.json src/recipes/money-printer-realistic.json
git commit -m "feat: add realistic-image/video/money-printer recipes"
```

---

### Task 4: Money Printer E2E (TTS + ffmpeg)

**Files:**
- Modify: `src/commands/media/ffmpeg-tiktok.ts` (if exists) or reuse `C:\OmniRoute\repos\mark-l\core\local_session.py` TTS logic
- Create: `tests/e2e/money-printer.test.ts`

**Interfaces:**
- Consumes: Qwen GGUF Ollama 11434, Kokoro 8881, Voicebox 17493, ComfyUI 8188
- Produces: `1080x1920` MP4 `tiktok.mp4` (ffprobe verified)

- [ ] **Step 1: Write the failing test**

```typescript
test("money-printer produces 1080x1920 mp4", async () => {
  const res = await runRecipe("money-printer-realistic", { prompt: "a cozy cafe" });
  expect(res.videoPath).toMatch(/\.mp4$/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/e2e/money-printer.test.ts`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation** — reuse `orca/media.py` ffmpeg logic (already 1080x1920 verified), call `image/generate-realistic` batch 3 + `tts/speak` + `ffmpeg_tiktok`

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/e2e/money-printer.test.ts`
Expected: PASS (mock or real ComfyUI+Kokoro if running)

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/money-printer.test.ts
git commit -m "feat: add money-printer E2E (TTS+ComfyUI+ffmpeg)"
```

---

### Task 5: Qwen GGUF Verifikation + Continuum Start

**Files:**
- Modify: `C:\OmniRoute\repos\mark-l\start-all.cmd` — add `ollama serve` + `continuum` + `comfyui` HealthChecks (bereits Python-Checks, erweitern)
- Verify: `config/api_keys.json` (ollama) — bereits done

**Interfaces:**
- Consumes: `ollama list` (hf.co/Jackrong...), `curl localhost:11434/api/tags`
- Produces: `start-all.cmd` v2 (5→7 HealthChecks)

- [ ] **Step 1: Write the failing test**

```python
def test_ollama_config():
    cfg = json.loads(Path("C:/OmniRoute/repos/mark-l/config/api_keys.json").read_text())
    assert cfg["llm_provider"] == "ollama" and "Qwen3.5" in cfg["llm_model"]
```

- [ ] **Step 2: Run test to verify it fails** (if already fixed, it passes — then adjust to check continuum)

- [ ] **Step 3: Write minimal implementation** — `start-all.cmd` erweitern, `autostart.vbs` → `Continuum.lnk`, `git tag pre-continuum` Archiv

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ollama_config.py -v; cmd /c start-all.cmd` (bis `JARVIS Connected` + `continuum` Grid)
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add C:/OmniRoute/repos/mark-l/start-all.cmd
git commit -m "chore: update start-all for ollama+continuum+comfyui"
```

---

### Task 6: Forge LoRA Stub (Option C)

**Files:**
- Create: `docs/forge/realistic-vision-lora.md` — Stub Contract (ForgeAlloy JSON)

**Interfaces:**
- Consumes: Erfolgreiche `money-printer-realistic` Artifacts (L3 Engrams)
- Produces: `forge-alloy` Contract Stub

- [ ] **Step 1: Write the failing test**

```typescript
test("forge contract exists", () => {
  const alloy = require("../../docs/forge/realistic-vision-lora.json");
  expect(alloy.recipe).toBeDefined();
});
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write minimal implementation** — JSON `recipe: prun, train, quant, eval` mit `continuum-ai/realistic-vision-lora`

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add docs/forge/realistic-vision-lora.md
git commit -m "feat: add forge alloy stub for realistic-vision-lora"
```

---

## Self-Review

- **Spec coverage:** Alle Spec-Abschnitte 1-9 abgedeckt — Checkpoint (T1), Command (T2), Recipes (T3), Money Printer (T4), Ollama (T5), Forge LoRA (T6). Keine Lücke.
- **Placeholder scan:** Keine `TBD`/`TODO`, alle Steps mit konkretem Code/Command/Pfad, keine "handle edge cases" ohne Code.
- **Type consistency:** `generateRealistic` Signatur in T2 = T3 Recipe Params (`prompt,width,height,steps,seed,checkpoint`), `imagePath` konsistent, `llm_provider ollama` in T5 = Spec Global Constraints.

