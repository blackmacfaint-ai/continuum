# Forge Alloy Stub — realistic-vision-lora

**Model:** `continuum-ai/realistic-vision-lora`  
**Base:** `realisticVisionV60B1_v51HyperVAE` (1.99GB SD1.5 HyperVAE) at `C:\OmniRoute\ComfyUI\models\checkpoints\realisticVisionV60B1_v51HyperVAE.safetensors`  
**Hardware:** AMD RX 6800 XT 16GB — GGUF Q4_K_M required for FLUX 12GB + Minimax 10GB sequential, auto-unload  
**Consumes:** Successful `money-printer-realistic` artifacts (L3 Engrams, 1080x1920 tiktok.mp4, realistic images from `image/generate-realistic`)  
**Produces:** `forge-alloy` Contract Stub (JSON `docs/forge/realistic-vision-lora.json`)

## Contract

JSON contract at `docs/forge/realistic-vision-lora.json` defines ForgeAlloy pipeline:

- `recipe.prun` — prune L3 Engrams dataset (dedupe, minScore 0.7)
- `recipe.train` — LoRA train on base realisticVision (rank 16, alpha 32, lr 1e-4, epochs 3)
- `recipe.quant` — GGUF Q4_K_M quantize for 16GB VRAM sequential execution
- `recipe.eval` — evaluate fid/clip_score/human_preference at 576x1024

## Interfaces

- Consumes: `money-printer-realistic` pipeline outputs via `artifacts/store`
- Produces: `continuum-ai/realistic-vision-lora` LoRA artifact for reuse by `image/generate-realistic` with optional LoRA loader

## Validation

Test: `src/tests/unit/forge-contract.test.ts` imports `../../../docs/forge/realistic-vision-lora.json` and asserts `recipe` defined and `model === "continuum-ai/realistic-vision-lora"` with prun/train/quant/eval present.

## Status

Option C stub — training not executed, contract only. Future work: `train --forge docs/forge/realistic-vision-lora.json` when L3 Engrams volume sufficient.
