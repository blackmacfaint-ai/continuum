#!/usr/bin/env python3
"""image/generate-realistic helper - ComfyUI txt2img (realisticVisionV60B1), batch N 576x1024.

Usage:
  python scripts/image_generate_realistic.py --prompt "a cozy cafe" --batch 3 --output C:/out
  python scripts/image_generate_realistic.py --prompt "..." --checkpoint realisticVisionV60B1_v51HyperVAE.safetensors

Prints JSON: {"success": true, "images": ["path1", ...], "seed": 123}
"""
import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_COMFY_HOST = "http://localhost:8188"
DEFAULT_CHECKPOINT = "realisticVisionV60B1_v51HyperVAE.safetensors"
DEFAULT_NEGATIVE = "blurry, low quality, distorted, deformed, bad anatomy"


def parse_args():
    ap = argparse.ArgumentParser(description="Generate photorealistic 576x1024 images via ComfyUI")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE)
    ap.add_argument("--width", type=int, default=576)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--cfg", type=float, default=7.0)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    ap.add_argument("--output", default="C:/OmniRoute/ComfyUI/output/continuum/realistic")
    ap.add_argument("--comfy-host", default=DEFAULT_COMFY_HOST)
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def build_workflow(prompt, negative, width, height, steps, cfg, seed, batch, checkpoint):
    return {
        "3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["3", 1]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["3", 1]}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": batch}},
        "7": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0, "model": ["3", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "continuum/realistic", "images": ["8", 0]}},
    }


def main() -> int:
    args = parse_args()
    if not args.prompt.strip():
        print(json.dumps({"success": False, "error": "prompt is required"}))
        return 1
    seed = args.seed if args.seed is not None else 177013
    if args.dry_run:
        print(json.dumps({"success": True, "images": [], "seed": seed, "dryRun": True}))
        return 0

    wf = build_workflow(args.prompt, args.negative_prompt, args.width, args.height,
                        args.steps, args.cfg, seed, args.batch, args.checkpoint)
    req = urllib.request.Request(
        args.comfy_host + "/prompt",
        data=json.dumps({"prompt": wf, "client_id": "continuum-image"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            pid = json.load(r)["prompt_id"]
    except urllib.error.HTTPError as e:
        print(json.dumps({"success": False, "error": f"ComfyUI POST /prompt: HTTP {e.code} {e.read().decode()[:300]}"}))
        return 1

    deadline = time.time() + 600
    images = []
    while time.time() < deadline:
        time.sleep(3)
        try:
            with urllib.request.urlopen(f"{args.comfy_host}/history/{pid}", timeout=10) as r:
                h = json.load(r)
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            continue
        if pid in h:
            entry = h[pid]
            st = entry.get("status", {})
            if st.get("status_str") == "error":
                print(json.dumps({"success": False, "error": "comfy job failed"}))
                return 1
            if st.get("status_str") == "success":
                out_dir = pathlib.Path(args.output)
                out_dir.mkdir(parents=True, exist_ok=True)
                for out in entry.get("outputs", {}).values():
                    for img in out.get("images", []):
                        dst = out_dir / img["filename"]
                        view = f"{args.comfy_host}/view?filename={urllib.parse.quote(img['filename'])}&subfolder={urllib.parse.quote(img.get('subfolder', ''))}&type=output"
                        urllib.request.urlretrieve(view, dst)
                        images.append(str(dst))
                break
    if not images:
        print(json.dumps({"success": False, "error": "no images generated"}))
        return 1
    print(json.dumps({"success": True, "images": images, "seed": seed}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
