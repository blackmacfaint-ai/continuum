#!/usr/bin/env python3
"""
Forge LoRA Training for realistic-vision-lora
Consumes money-printer-realistic artifacts, produces continuum-ai/realistic-vision-lora

Recipe from docs/forge/realistic-vision-lora.json:
  prun -> train (rank16 alpha32 lr0.0001 epochs3) -> quant Q4_K_M -> eval

This stub prepares dataset and creates placeholder LoRA. For real training, replace train step with:
  accelerate launch --mixed_precision=fp16 train_text_to_image_lora.py \
    --pretrained_model_name_or_path="runwayml/stable-diffusion-v1-5" \
    --instance_data_dir="data/money_printer" --output_dir="models/lora/realistic-vision-lora" \
    --rank=16 --lora_alpha=32 --learning_rate=0.0001 --max_train_steps=600 --train_batch_size=1

Hardware: AMD RX 6800 XT 12GB (now 12288 MB) via directml privateuseone, GGUF Q4_K_M for sequential FLUX/Minimax.
"""
import argparse
import json
import pathlib
import shutil
import sys

FORGE_JSON = pathlib.Path(__file__).parent.parent / "docs" / "forge" / "realistic-vision-lora.json"
DEFAULT_ARTIFACTS = [
    pathlib.Path(r"C:\OmniRoute\ComfyUI\output\money_printer_v2"),
    pathlib.Path(r"C:\OmniRoute\ComfyUI\output\money_printer"),
]

def load_forge():
    return json.loads(FORGE_JSON.read_text(encoding="utf-8"))

def prun_step(artifacts_dir: pathlib.Path, output_dir: pathlib.Path, min_score: float = 0.7):
    """Prune: dedupe and filter by minScore 0.7 (mock scoring based on file size)"""
    output_dir.mkdir(parents=True, exist_ok=True)
    images = list(artifacts_dir.glob("image_*.png"))
    if not images:
        images = list(artifacts_dir.glob("*.png"))
    print(f"PRUN: found {len(images)} images in {artifacts_dir}")
    kept = []
    seen = set()
    for img in sorted(images):
        # dedupe by size
        size = img.stat().st_size
        if size in seen:
            print(f"  dedupe skip {img.name} size {size}")
            continue
        seen.add(size)
        # mock score: larger files = higher quality, normalize 0-1
        score = min(1.0, size / 1000000)
        if score < min_score:
            print(f"  filter skip {img.name} score {score:.2f} < {min_score}")
            continue
        dest = output_dir / img.name
        shutil.copy2(img, dest)
        kept.append(dest)
        print(f"  kept {img.name} score {score:.2f} -> {dest}")
    print(f"PRUN: kept {len(kept)}/{len(images)}")
    return kept

def train_step(pruned_dir: pathlib.Path, output_dir: pathlib.Path, base: str, rank: int, alpha: int, lr: float, epochs: int):
    """Train: LoRA rank16 alpha32 lr0.0001 epochs3 - stub creates placeholder safetensors"""
    output_dir.mkdir(parents=True, exist_ok=True)
    # Check base checkpoint exists
    base_path = pathlib.Path(r"C:\OmniRoute\ComfyUI\models\checkpoints\realisticVisionV60B1_v51HyperVAE.safetensors")
    if not base_path.exists():
        print(f"WARNING: base {base_path} not found", file=sys.stderr)
    # Create dummy LoRA file
    lora_path = output_dir / "pytorch_lora_weights.safetensors"
    # Create minimal safetensors header (dummy)
    dummy = {
        "lora_unet_down_blocks_0_attentions_0_transformer_blocks_0_attn1_to_q.lora_A.weight": [rank, 320],
        "lora_unet_down_blocks_0_attentions_0_transformer_blocks_0_attn1_to_q.lora_B.weight": [320, rank],
    }
    # Write as json for stub (real safetensors would be binary)
    lora_path.write_text(json.dumps({"stub": True, "rank": rank, "alpha": alpha, "base": base, "epochs": epochs, "dummy_keys": list(dummy.keys())}, indent=2), encoding="utf-8")
    # Also create adapter_config.json
    (output_dir / "adapter_config.json").write_text(json.dumps({
        "base_model_name_or_path": base,
        "r": rank,
        "lora_alpha": alpha,
        "lora_dropout": 0.0,
        "target_modules": ["to_q", "to_k", "to_v", "to_out.0"],
        "task_type": "CAUSAL_LM" if False else "DIFFUSION",
        "inference_mode": True
    }, indent=2), encoding="utf-8")
    print(f"TRAIN: stub LoRA created at {lora_path} rank={rank} alpha={alpha} lr={lr} epochs={epochs}")
    # Create train log
    (output_dir / "train.log").write_text(f"Stub training with {len(list(pruned_dir.glob('*.png')))} images\nBase: {base}\nRank: {rank} Alpha: {alpha} LR: {lr} Epochs: {epochs}\nHardware: AMD RX 6800 XT 12GB directml privateuseone\nStatus: stub - replace with real accelerate training\n", encoding="utf-8")
    return lora_path

def quant_step(lora_dir: pathlib.Path, output_path: pathlib.Path, quant: str = "Q4_K_M"):
    """Quant: GGUF Q4_K_M stub"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Create dummy GGUF
    output_path.write_text(json.dumps({"stub": True, "quant": quant, "source": str(lora_dir), "purpose": "FLUX 12GB + Minimax 10GB sequential on 12GB VRAM"}, indent=2), encoding="utf-8")
    print(f"QUANT: stub GGUF {quant} at {output_path}")
    return output_path

def eval_step(lora_dir: pathlib.Path, metrics: list, resolution: str = "576x1024"):
    """Eval: fid, clip_score, human_preference stub"""
    results = {}
    for m in metrics:
        # Mock scores
        if m == "fid":
            results[m] = 12.5  # lower is better
        elif m == "clip_score":
            results[m] = 0.31
        elif m == "human_preference":
            results[m] = 0.78
        else:
            results[m] = 0.5
    eval_path = lora_dir / "eval.json"
    eval_path.write_text(json.dumps({"metrics": results, "resolution": resolution, "samplePrompts": 20, "stub": True}, indent=2), encoding="utf-8")
    print(f"EVAL: {results} -> {eval_path}")
    return results

def main():
    ap = argparse.ArgumentParser(description="Forge realistic-vision-lora training")
    ap.add_argument("--artifacts", default=None, help="Path to money-printer artifacts dir")
    ap.add_argument("--output", default="models/lora/realistic-vision-lora", help="Output LoRA dir")
    ap.add_argument("--quant-output", default="models/lora/realistic-vision-lora-Q4_K_M.gguf", help="Quantized GGUF output")
    ap.add_argument("--dry-run", action="store_true", help="Validate only")
    args = ap.parse_args()

    forge = load_forge()
    print(f"Forge {forge['model']} base {forge['base']}")

    artifacts_dir = pathlib.Path(args.artifacts) if args.artifacts else None
    if not artifacts_dir or not artifacts_dir.exists():
        for cand in DEFAULT_ARTIFACTS:
            if cand.exists() and list(cand.glob("*.png")):
                artifacts_dir = cand
                break
    if not artifacts_dir or not artifacts_dir.exists():
        print(f"ERROR: artifacts dir not found. Tried {DEFAULT_ARTIFACTS}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"DRY-RUN OK: artifacts {artifacts_dir} forge {FORGE_JSON}")
        sys.exit(0)

    # Step 1: prun
    pruned_dir = pathlib.Path("data/money_printer_pruned")
    kept = prun_step(artifacts_dir, pruned_dir, min_score=forge["recipe"]["prun"]["params"]["minScore"])

    # Step 2: train
    output_dir = pathlib.Path(args.output)
    train_cfg = forge["recipe"]["train"]["params"]
    train_step(pruned_dir, output_dir, forge["recipe"]["train"]["base"], train_cfg["rank"], train_cfg["alpha"], train_cfg["learningRate"], train_cfg["epochs"])

    # Step 3: quant
    quant_cfg = forge["recipe"]["quant"]["params"]
    quant_step(output_dir, pathlib.Path(args.quant_output), quant_cfg["quant"])

    # Step 4: eval
    eval_cfg = forge["recipe"]["eval"]
    eval_step(output_dir, eval_cfg["metrics"], eval_cfg["params"]["resolution"])

    print(f"DONE: LoRA stub at {output_dir} and {args.quant_output}")
    print(f"Next: replace stub with real training via accelerate + PEFT on {pruned_dir}")

if __name__ == "__main__":
    main()
