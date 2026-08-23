# Money Printer E2E-Produktionslauf Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den `money-printer-realistic`-Rezept-Lauf end-to-end lauffähig machen — vom deutschen Script über Bild, Video, Voiceover, Untertitel und 1080×1920-Export bis zur Artifact-Registry (Uploads bleiben Stubs, da Credentials fehlen).

**Architecture:** Drei neue/vervollständigte Commands (`tts/speak`, `artifacts/store`, `video/generate` [bereits implementiert]) folgen dem etablierten Continuum-Muster: TS-Scaffold (`shared/`-Typen + `server/` + `browser/`-Command) delegiert an einen Python-Helper in `scripts/`, verifiziert per pytest + ruff. Das Rezept wird auf die realen Command-Namen/Parameter verdrahtet; ein E2E-Test läuft die Helper-Kette einmal komplett durch.

**Tech Stack:** Python 3.12 (stdlib: urllib, subprocess, json), Kokoro-DE HTTP (8881, `martin`), Voicebox HTTP (17493, Profil „Overlay DE"), ComfyUI HTTP (8188, realisticVisionV60B1), ffmpeg 9.0, pytest, ruff, TypeScript-Scaffold (deklarativ, ohne Build-Ausführung — node_modules leer).

**Spec:** Brainstorming-Entscheid 2026-08-23: Meilenstein = E2E-Produktionslauf (Uploads bleiben Stubs). Siehe `src/recipes/money-printer-realistic.json` als Verhaltens-Spezifikation.

## Global Constraints

- Verifikation ausschließlich via `python -m pytest tests/` und `ruff check` (node_modules ist leer — keine vitest/tsx-Läufe).
- Commands folgen dem youtube/upload- & video/generate-Muster: `src/commands/<ns>/<name>/shared/*Types.ts` + `server/*ServerCommand.ts` + `browser/*BrowserCommand.ts` + `tools/generator/specs/<ns>-<name>.json` (Ownership-Guard) + Python-Helper + pytest.
- `generated.ts` NICHT manuell editieren — wird beim Build regeneriert (Precommit blockt).
- Uploads (youtube/upload) bleiben Stubs; echte Credentials (`config/client_secrets.json`) sind User-Aufgabe.
- Python-Helper geben JSON auf stdout aus, Exit 0 bei Erfolg, Exit ≠ 0 bei Fehler.
- Keine Zugangsdaten in Logs/Commits.

---

### Task 1: `tts/speak` Command (Kokoro-DE + Voicebox-Fallback)

**Files:**
- Create: `src/commands/tts/speak/shared/TtsSpeakTypes.ts`
- Create: `src/commands/tts/speak/server/TtsSpeakServerCommand.ts`
- Create: `src/commands/tts/speak/browser/TtsSpeakBrowserCommand.ts`
- Create: `tools/generator/specs/tts-speak.json`
- Create: `scripts/tts_speak.py`
- Create: `tests/test_tts_speak.py`

**Interfaces:**
- Consumes: `../../../../system/core/types/JTAGTypes` (`CommandParams`, `JTAGPayload`, `CommandInput`), `../../../../daemons/command-daemon/shared/CommandBase`
- Produces: `ttsSpeak(params: TtsSpeakParams): Promise<TtsSpeakResult>`; `TtsSpeakResult { success: boolean; audioPath?: string; engine?: string; duration?: number; error?: string }`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tts_speak.py
import json, pathlib, subprocess, sys

REPO = pathlib.Path(__file__).parent.parent

def run_helper(*args):
    return subprocess.run([sys.executable, str(REPO / "scripts" / "tts_speak.py"), *args],
                          capture_output=True, text=True, cwd=REPO, check=False)

def test_helper_exists():
    p = REPO / "scripts" / "tts_speak.py"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "kokoro" in content and "voicebox" in content

def test_types_exist():
    p = REPO / "src" / "commands" / "tts" / "speak" / "shared" / "TtsSpeakTypes.ts"
    assert p.exists()
    assert "tts/speak" in p.read_text(encoding="utf-8")
    assert "ttsSpeak" in p.read_text(encoding="utf-8")

def test_spec_exists():
    p = REPO / "tools" / "generator" / "specs" / "tts-speak.json"
    spec = json.loads(p.read_text(encoding="utf-8"))
    assert spec["name"] == "tts/speak"
    assert spec["accessLevel"] == "ai-safe"

def test_dry_run_rejects_missing_text():
    r = run_helper("--text", "", "--dry-run")
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["success"] is False and "text" in out["error"]

def test_dry_run_ok():
    r = run_helper("--text", "Hallo Welt", "--dry-run")
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["success"] is True and out["dryRun"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tts_speak.py -v`
Expected: FAIL (dateien fehlen: `FileNotFoundError` / ModuleNotFoundError)

- [ ] **Step 3: Create `scripts/tts_speak.py`**

```python
#!/usr/bin/env python3
"""tts/speak helper - Kokoro-DE (8881, martin) mit Voicebox-Fallback (17493, 'Overlay DE')."""
import argparse, json, pathlib, subprocess, sys, time, urllib.request

KOKORO_URL = "http://localhost:8881/v1/audio/speech"
VOICEBOX_URL = "http://127.0.0.1:17493"
REPO_ROOT = pathlib.Path(__file__).parent.parent

def parse_args():
    ap = argparse.ArgumentParser(description="TTS: Kokoro-DE mit Voicebox-Fallback")
    ap.add_argument("--text", required=True)
    ap.add_argument("--voice", default="martin")
    ap.add_argument("--engine", choices=["kokoro", "voicebox"], default="kokoro")
    ap.add_argument("--fallback-engine", choices=["kokoro", "voicebox", "none"], default="voicebox")
    ap.add_argument("--lang", default="de")
    ap.add_argument("--profile", default="Overlay DE")
    ap.add_argument("--output", default=None)
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()

def kokoro_speak(text, voice, out_path):
    body = json.dumps({"text": text, "voice": voice, "response_format": "mp3"}).encode()
    req = urllib.request.Request(KOKORO_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    out_path.write_bytes(data)
    return out_path

def voicebox_speak(text, profile, out_path):
    gen = json.dumps({"text": text, "profile": profile}).encode()
    req = urllib.request.Request(VOICEBOX_URL + "/generate", data=gen,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        gid = json.load(r)["generation_id"]
    for _ in range(120):
        time.sleep(3)
        with urllib.request.urlopen(VOICEBOX_URL + f"/history/{gid}", timeout=10) as r:
            h = json.load(r)
        if h.get("status") == "completed":
            break
    with urllib.request.urlopen(VOICEBOX_URL + f"/audio/{gid}", timeout=30) as r:
        out_path.write_bytes(r.read())
    return out_path

def main():
    args = parse_args()
    if not args.text.strip():
        print(json.dumps({"success": False, "error": "text is required"})); return 1
    out = pathlib.Path(args.output) if args.output else (REPO_ROOT / "data" / "audio" / "voice.wav")
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        print(json.dumps({"success": True, "audioPath": str(out), "engine": args.engine,
                          "dryRun": True})); return 0
    engine = args.engine
    try:
        if engine == "kokoro":
            kokoro_speak(args.text, args.voice, out)
        else:
            voicebox_speak(args.text, args.profile, out)
    except Exception as e:
        if args.fallback_engine == "none":
            print(json.dumps({"success": False, "error": f"{engine}: {e}"})); return 1
        print(f"WARN {engine} failed ({e}), fallback {args.fallback_engine}", file=sys.stderr)
        engine = args.fallback_engine
        try:
            if engine == "kokoro":
                kokoro_speak(args.text, args.voice, out)
            else:
                voicebox_speak(args.text, args.profile, out)
        except Exception as e2:
            print(json.dumps({"success": False, "error": f"{engine}: {e2}"})); return 1
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
                         capture_output=True, text=True, check=False).stdout.strip()
    print(json.dumps({"success": True, "audioPath": str(out), "engine": engine,
                      "duration": float(dur) if dur else None}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Create `src/commands/tts/speak/shared/TtsSpeakTypes.ts`**

```ts
import type { CommandParams, JTAGPayload, CommandInput } from '../../../../system/core/types/JTAGTypes';
import * as fs from 'fs';
import * as path from 'path';
import { execFile } from 'child_process';

export interface TtsSpeakParams extends CommandParams {
  text: string;
  voice?: string;
  engine?: 'kokoro' | 'voicebox';
  fallbackEngine?: 'kokoro' | 'voicebox' | 'none';
  lang?: string;
  profile?: string;
  output?: string;
}

export interface TtsSpeakResult extends JTAGPayload {
  success: boolean;
  audioPath?: string;
  engine?: string;
  duration?: number;
  error?: string;
}

export function createTtsSpeakResult(params: TtsSpeakParams, outcome: Partial<TtsSpeakResult>): TtsSpeakResult {
  return {
    success: outcome.success ?? false,
    audioPath: outcome.audioPath,
    engine: outcome.engine,
    duration: outcome.duration,
    error: outcome.error,
    context: params.context,
    sessionId: params.sessionId,
  };
}

function findHelper(): string | null {
  const candidates = [
    path.resolve(process.cwd(), 'scripts', 'tts_speak.py'),
    path.resolve(__dirname, '../../../../../scripts/tts_speak.py'),
    'C:/OmniRoute/repos/continuum/scripts/tts_speak.py',
  ];
  for (const p of candidates) {
    try { if (fs.existsSync(p) && fs.statSync(p).isFile()) return p; } catch {}
  }
  return null;
}

export async function ttsSpeak(params: TtsSpeakParams): Promise<TtsSpeakResult> {
  if (!params.text || !params.text.trim()) {
    return createTtsSpeakResult(params, { success: false, error: 'text is required' });
  }
  const helper = findHelper();
  if (!helper) return createTtsSpeakResult(params, { success: false, error: 'scripts/tts_speak.py not found' });
  const args = [helper, '--text', params.text];
  if (params.voice) args.push('--voice', params.voice);
  if (params.engine) args.push('--engine', params.engine);
  if (params.fallbackEngine) args.push('--fallback-engine', params.fallbackEngine);
  if (params.lang) args.push('--lang', params.lang);
  if (params.profile) args.push('--profile', params.profile);
  if (params.output) args.push('--output', params.output);
  try {
    const stdout = await new Promise<string>((resolve, reject) => {
      execFile('python', args, { cwd: path.resolve(helper, '../..'), timeout: 120000, maxBuffer: 8 * 1024 * 1024 },
        (error, stdout, stderr) => error ? reject(new Error(stderr ? stderr.toString().slice(0, 800) : error.message)) : resolve(stdout.toString()));
    });
    return createTtsSpeakResult(params, JSON.parse(stdout) as TtsSpeakResult);
  } catch (err) {
    return createTtsSpeakResult(params, { success: false, error: `tts_speak.py failed: ${err instanceof Error ? err.message : String(err)}` });
  }
}

export const TtsSpeak = {
  async execute(params: CommandInput<TtsSpeakParams>): Promise<TtsSpeakResult> {
    const { Commands } = await import('../../../../system/core/shared/Commands');
    return Commands.execute<TtsSpeakParams, TtsSpeakResult>('tts/speak', params as Partial<TtsSpeakParams>);
  },
  commandName: 'tts/speak' as const,
} as const;
```

- [ ] **Step 5: Create server + browser commands**

`src/commands/tts/speak/server/TtsSpeakServerCommand.ts` (Muster: `VideoGenerateServerCommand`, `super('tts/speak', ...)`, `execute` → `ttsSpeak(p)` in try/catch) und `src/commands/tts/speak/browser/TtsSpeakBrowserCommand.ts` (Stub: `{ success: false, error: 'tts/speak not supported in browser - use server' }`).

- [ ] **Step 6: Create `tools/generator/specs/tts-speak.json`**

```json
{
  "name": "tts/speak",
  "description": "Text-to-speech via Kokoro-DE (8881, martin) with Voicebox fallback (17493, Overlay DE). Returns the audio file path and engine used.",
  "params": [
    { "name": "text", "type": "string", "description": "Text to synthesize" },
    { "name": "voice", "type": "string", "optional": true, "description": "Kokoro voice (default martin)" },
    { "name": "engine", "type": "string", "optional": true, "description": "kokoro | voicebox (default kokoro)" },
    { "name": "fallbackEngine", "type": "string", "optional": true, "description": "kokoro | voicebox | none" },
    { "name": "lang", "type": "string", "optional": true, "description": "Language (default de)" },
    { "name": "profile", "type": "string", "optional": true, "description": "Voicebox profile (default Overlay DE)" },
    { "name": "output", "type": "string", "optional": true, "description": "Output audio path" }
  ],
  "results": [
    { "name": "success", "type": "boolean" },
    { "name": "audioPath", "type": "string" },
    { "name": "engine", "type": "string" },
    { "name": "duration", "type": "number", "optional": true },
    { "name": "error", "type": "string", "optional": true }
  ],
  "accessLevel": "ai-safe",
  "environment": "server"
}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/test_tts_speak.py -v && ruff check scripts/tts_speak.py tests/test_tts_speak.py`
Expected: 5 PASSED, `All checks passed!`

- [ ] **Step 8: Commit**

```bash
git add tools/generator/specs/tts-speak.json src/commands/tts scripts/tts_speak.py tests/test_tts_speak.py
git commit -m "feat: add tts/speak command (Kokoro-DE + Voicebox fallback)"
```

---

### Task 2: `artifacts/store` Command (Artifact-Registry)

**Files:**
- Create: `src/commands/artifacts/store/shared/ArtifactsStoreTypes.ts`
- Create: `src/commands/artifacts/store/server/ArtifactsStoreServerCommand.ts`
- Create: `src/commands/artifacts/store/browser/ArtifactsStoreBrowserCommand.ts`
- Create: `tools/generator/specs/artifacts-store.json`
- Create: `scripts/artifacts_store.py`
- Create: `tests/test_artifacts_store.py`

**Interfaces:**
- Consumes: JTAGTypes (wie Task 1)
- Produces: `storeArtifact(params: ArtifactsStoreParams): Promise<ArtifactsStoreResult>`; `ArtifactsStoreResult { success: boolean; artifactId?: string; path?: string; error?: string }`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_artifacts_store.py
import json, pathlib, subprocess, sys, tempfile

REPO = pathlib.Path(__file__).parent.parent

def run_helper(*args):
    return subprocess.run([sys.executable, str(REPO / "scripts" / "artifacts_store.py"), *args],
                          capture_output=True, text=True, cwd=REPO, check=False)

def test_helper_exists():
    assert (REPO / "scripts" / "artifacts_store.py").exists()

def test_types_exist():
    p = REPO / "src" / "commands" / "artifacts" / "store" / "shared" / "ArtifactsStoreTypes.ts"
    content = p.read_text(encoding="utf-8")
    assert "artifacts/store" in content and "storeArtifact" in content

def test_spec_exists():
    spec = json.loads((REPO / "tools" / "generator" / "specs" / "artifacts-store.json").read_text(encoding="utf-8"))
    assert spec["name"] == "artifacts/store"

def test_store_registers_artifact(tmp_path):
    art = tmp_path / "clip.mp4"
    art.write_bytes(b"\x00" * 2048)
    reg = tmp_path / "registry.json"
    r = run_helper("--artifact", str(art), "--type", "video", "--registry", str(reg))
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["success"] is True and out["artifactId"]
    entries = json.loads(reg.read_text(encoding="utf-8"))
    assert len(entries) == 1 and entries[0]["type"] == "video" and entries[0]["artifactId"] == out["artifactId"]

def test_store_rejects_missing_file():
    r = run_helper("--artifact", r"C:\nope\missing.mp4", "--type", "video")
    assert r.returncode == 1
    assert json.loads(r.stdout)["success"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_artifacts_store.py -v`
Expected: FAIL (fehlende Dateien)

- [ ] **Step 3: Create `scripts/artifacts_store.py`**

```python
#!/usr/bin/env python3
"""artifacts/store helper - kopiert Artefakt nach data/artifacts/<type>/<id>.<ext> und registriert es."""
import argparse, json, pathlib, shutil, sys, uuid

REPO_ROOT = pathlib.Path(__file__).parent.parent
DEFAULT_REGISTRY = REPO_ROOT / "data" / "artifacts" / "registry.json"

def parse_args():
    ap = argparse.ArgumentParser(description="Store artifact in registry")
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--type", choices=["video", "image", "audio", "document"], required=True)
    ap.add_argument("--tags", nargs="*", default=[])
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()

def main():
    args = parse_args()
    src = pathlib.Path(args.artifact)
    if not src.exists():
        print(json.dumps({"success": False, "error": f"artifact not found: {src}"})); return 1
    artifact_id = uuid.uuid4().hex[:12]
    registry = pathlib.Path(args.registry)
    if args.dry_run:
        print(json.dumps({"success": True, "artifactId": artifact_id,
                          "path": str(src), "dryRun": True})); return 0
    target_dir = registry.parent / "files" / args.type
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{artifact_id}{src.suffix.lower()}"
    shutil.copy2(src, target)
    entries = []
    if registry.exists():
        entries = json.loads(registry.read_text(encoding="utf-8"))
    entries.append({
        "artifactId": artifact_id, "type": args.type, "path": str(target),
        "source": str(src), "tags": args.tags, "createdAt": "2026-08-23",
    })
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(json.dumps({"success": True, "artifactId": artifact_id, "path": str(target)}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Create `src/commands/artifacts/store/shared/ArtifactsStoreTypes.ts`** (Muster Task 1, aber `storeArtifact()` statt `ttsSpeak()`, Helper `scripts/artifacts_store.py`, Args `--artifact/--type/--tags/--registry`; Result `{ success, artifactId, path, error }`)

- [ ] **Step 5: Create server + browser commands + `tools/generator/specs/artifacts-store.json`** (Muster Task 1; accessLevel `ai-safe`, environment `server`)

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_artifacts_store.py -v && ruff check scripts/artifacts_store.py tests/test_artifacts_store.py`
Expected: 5 PASSED, `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add tools/generator/specs/artifacts-store.json src/commands/artifacts scripts/artifacts_store.py tests/test_artifacts_store.py
git commit -m "feat: add artifacts/store command (artifact registry)"
```

---

### Task 3: Rezept-Verdrahtung `money-printer-realistic.json`

**Files:**
- Modify: `src/recipes/money-printer-realistic.json` (Pipeline-Steps)
- Create: `tests/test_money_printer_recipe.py`

**Interfaces:**
- Consumes: Recipe-Step-Namen → reale Commands: `tts/speak`, `video/generate`, `artifacts/store`, `ffmpeg_tiktok` (bestehend), `youtube/upload` (Stub bleibt)
- Produces: geprüfte Rezept-Struktur (Test liest JSON und validiert Command-Namen + Parameter-Verknüpfungen)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_money_printer_recipe.py
import json, pathlib

REPO = pathlib.Path(__file__).parent.parent
RECIPE = REPO / "src" / "recipes" / "money-printer-realistic.json"
KNOWN = {"rag/build", "ai/should-respond", "ai/generate", "tts/speak",
         "image/generate-realistic", "video/generate", "ffmpeg_tiktok",
         "artifacts/store", "youtube/upload"}

def test_recipe_commands_exist():
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    for step in recipe["pipeline"]:
        assert step["command"] in KNOWN, f"unbekanntes Command: {step['command']}"

def test_recipe_command_dirs_exist():
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    for step in recipe["pipeline"]:
        cmd = step["command"]
        if cmd in ("rag/build", "ai/should-respond", "ai/generate", "ffmpeg_tiktok", "youtube/upload"):
            continue  # bestehende Commands
        assert (REPO / "src" / "commands" / *cmd.split("/")).exists(), f"fehlt: {cmd}"

def test_tts_step_has_kokoro_and_voicebox_fallback():
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    tts = next(s for s in recipe["pipeline"] if s["command"] == "tts/speak")
    assert tts["params"]["engine"] == "kokoro"
    assert tts["params"]["fallbackEngine"] == "voicebox"
    assert tts["params"]["profile"] == "Overlay DE"

def test_video_step_fallback_ken_burns():
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    vid = next(s for s in recipe["pipeline"] if s["command"] == "video/generate")
    assert vid["params"]["fallback"] == "ken-burns"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_money_printer_recipe.py -v`
Expected: FAIL bei `tts/speak` (kein Command-Verzeichnis, keine Spec) — `test_recipe_command_dirs_exist` und `test_tts_step_has_kokoro_and_voicebox_fallback`

- [ ] **Step 3: Align the recipe JSON** — Setze `tts/speak`-Params auf `engine: kokoro`, `fallbackEngine: voicebox`, `voice: martin`, `lang: de`, `profile: Overlay DE`; `video/generate`-Params um `fallback: ken-burns` und `baseImage`-Referenz auf den `outputTo` des `image/generate-realistic`-Steps (`baseFrame`); `artifacts/store`-Step auf `{"artifact": "$tiktokVideo", "type": "video"}`. JSON-Validität prüfen: `python -c "import json; json.load(open('src/recipes/money-printer-realistic.json',encoding='utf-8'))"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_money_printer_recipe.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/recipes/money-printer-realistic.json tests/test_money_printer_recipe.py
git commit -m "feat: wire money-printer-realistic recipe to tts/speak + artifacts/store + video/generate"
```

---

### Task 4: E2E-Produktionslauf-Verifikation

**Files:**
- Create: `tests/test_money_printer_e2e.py`
- Create: `docs/superpowers/plans/2026-08-23-money-printer-e2e-RUNLOG.md` (Ausführungs-Log beim echten Lauf)

**Interfaces:**
- Consumes: alle Helper aus Task 1–3 + bestehende (`scripts/video_generate.py`, `ffmpeg_tiktok`-Command)
- Produces: verifizierte Helper-Kette + dokumentierter manueller Lauf (Bild → Video → Audio → Export)

- [ ] **Step 1: Write the E2E smoke test (dry-run-Kette)**

```python
# tests/test_money_printer_e2e.py
import json, pathlib, subprocess, sys

REPO = pathlib.Path(__file__).parent.parent

def run(name, *args):
    return subprocess.run([sys.executable, str(REPO / "scripts" / name), *args],
                          capture_output=True, text=True, cwd=REPO, check=False)

def test_e2e_dry_run_chain():
    base = REPO / "data" / "money_printer_pruned" / "image_0.png"
    assert base.exists()
    r1 = run("video_generate.py", "--base-image", str(base), "--frames", "6", "--fps", "24", "--dry-run")
    assert r1.returncode == 0 and json.loads(r1.stdout)["dryRun"] is True
    r2 = run("tts_speak.py", "--text", "Hallo, dies ist ein Test.", "--dry-run")
    assert r2.returncode == 0 and json.loads(r2.stdout)["dryRun"] is True
    r3 = run("artifacts_store.py", "--artifact", str(base), "--type", "image", "--dry-run")
    assert r3.returncode == 0 and json.loads(r3.stdout)["dryRun"] is True

def test_e2e_artifacts_exist():
    assert (REPO / "scripts" / "video_generate.py").exists()
    assert (REPO / "scripts" / "tts_speak.py").exists()
    assert (REPO / "scripts" / "artifacts_store.py").exists()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_money_printer_e2e.py -v`
Expected: FAIL (tts_speak.py fehlt noch)

- [ ] **Step 3: Run the real production chain (manuell, dokumentiert)** — Stack vorher prüfen (`curl localhost:8188/system_stats`, `curl localhost:8881/docs`, `curl localhost:17493/profiles`), dann:

```bash
python scripts/tts_speak.py --text "$(python - <<'EOF'
print('Die Menschen, die dir am naechsten stehen, sind oft die, die du am meisten uebersiehst.')
EOF
)" --voice martin --engine kokoro --fallback-engine voicebox --output C:/OmniRoute/ComfyUI/output/money_printer_e2e/voice.wav

python scripts/video_generate.py --base-image C:/OmniRoute/ComfyUI/output/user_test_360_00001_.png \
  --prompt "drone shot flying over a forest at golden hour" --frames 6 --fps 24 \
  --output C:/OmniRoute/ComfyUI/output/money_printer_e2e/broll.mp4

python scripts/artifacts_store.py --artifact C:/OmniRoute/ComfyUI/output/money_printer_e2e/broll.mp4 --type video --tags e2e
```

- [ ] **Step 4: Dokumentiere Ergebnis** in `docs/superpowers/plans/2026-08-23-money-printer-e2e-RUNLOG.md` (JSON-Outputs, ffprobe-Daten, Fehler falls vorhanden)

- [ ] **Step 5: Commit**

```bash
git add tests/test_money_printer_e2e.py docs/superpowers/plans/2026-08-23-money-printer-e2e-RUNLOG.md
git commit -m "test: money-printer E2E production chain verification"
```

---

## Self-Review

**Spec-Abdeckung:** Recipe-Pipeline-Steps → `rag/build` (bestehend), `ai/should-respond` (bestehend), `ai/generate` (bestehend), `tts/speak` (Task 1), `image/generate-realistic` (bestehend), `video/generate` (bestehend, ken-burns), `ffmpeg_tiktok` (bestehend), `artifacts/store` (Task 2), `youtube/upload` (Stub bleibt — Credentials fehlen). Rezept-Verdrahtung = Task 3, E2E-Verifikation = Task 4.

**Typ-Konsistenz:** `TtsSpeakResult`/`ArtifactsStoreResult` folgen exakt dem `VideoGenerateResult`-Muster (JTAGPayload + success/error). Helper-Argumente in TS (`--text`, `--artifact`, `--type`) stimmen mit den argparse-Flags der Python-Helper überein. `ffmpeg_tiktok`-Params (`width/height/fps/subtitles/subtitleLang`) existieren bereits in `FFmpegTiktokParams`.

**Grenzen (bewusst im Scope):** Uploads (youtube/upload) bleiben Stubs; `generated.ts` wird beim Build regeneriert; echte minimax-h3/zImageTurbo-Motion ist eigener Folgemeilenstein.
