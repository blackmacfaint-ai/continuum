#!/usr/bin/env python3
"""
video/generate helper for continuum realistic-video recipe.

Animate a base frame into a short 720p video:
  1. Generate N sequential img2img frames via ComfyUI (360-degree turn choreography),
     keeping the same seed for character/appearance consistency.
  2. Stitch frames with ffmpeg Ken-Burns (zoompan) + crossfades at `--fps`.

Prefers minimax-h3 / zImageTurbo when the ComfyUI model files are present
(sequential generation). Falls back to ken-burns otherwise, per recipe
`fallback: "ken-burns"`.

Usage:
  python scripts/video_generate.py --base-image C:/OmniRoute/ComfyUI/output/user_test_360_00001_.png \
      --prompt "full 360-degree character showcase turn" --frames 6 --fps 24 --dry-run
  python scripts/video_generate.py --base-image <png> --prompt "<motion>" \
      --model minimax-h3 --fallback ken-burns --output C:/tmp/turn.mp4
  # Mehrere Basisbilder (Rezept: baseImage als Array) in EINEM Lauf -> ein Video:
  python scripts/video_generate.py --base-images img1.png,img2.png,img3.png \
      --prompt "cinematic slow pan" --frames 6 --output C:/tmp/broll.mp4

Prints a JSON result on stdout:
  {"success": true, "videoPath": "...", "frames": 6, "model": "ken-burns", "duration": 4.75}
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = pathlib.Path(__file__).parent.parent
DEFAULT_COMFY_HOST = "http://localhost:8188"
DEFAULT_CHECKPOINT = "realisticVisionV60B1_v51HyperVAE.safetensors"
DEFAULT_LORA = "realistic-vision-lora-rank16.safetensors"
DEFAULT_NEGATIVE = "blurry, low quality, distorted, deformed, bad anatomy"
COMFY_DIRS = ["C:/OmniRoute/ComfyUI", "C:/OmniRoute/repos/ComfyUI"]

# 360-degree character-showcase choreography (frame name -> angle wording)
ANGLES = [
    ("front", "facing the camera directly, front view, standing tall"),
    ("turn-right", "turning to his right, three-quarter view, right profile visible"),
    ("back", "turned away from camera, back view, slight glance over shoulder"),
    ("turn-left", "turning to his left, three-quarter view, left profile visible"),
    ("wave", "front view again, raising his right hand and waving to the audience"),
    ("front-close", "front view, full body pose, arms slightly out, confident stance"),
]


def find_comfy_root() -> pathlib.Path | None:
    for d in COMFY_DIRS:
        p = pathlib.Path(d)
        if (p / "models" / "checkpoints").exists():
            return p
    return None


def model_files_available(model: str) -> tuple[bool, list[str]]:
    """Check whether a minimax-h3 / zImageTurbo model file exists in ComfyUI."""
    root = find_comfy_root()
    if not root:
        return False, []
    needles = {
        "minimax-h3": ["minimax"],
        "zimage-turbo": ["zimage", "z-image"],
    }.get(model, [])
    found = []
    for sub in ["diffusion_models", "checkpoints", "unet", "loras"]:
        d = root / "models" / sub
        if not d.exists():
            continue
        for f in d.iterdir():
            if f.suffix.lower() in (".safetensors", ".gguf") and any(n in f.name.lower() for n in needles):
                found.append(str(f))
    return bool(found), found


def comfy_host_alive(host: str) -> bool:
    try:
        with urllib.request.urlopen(f"{host}/system_stats", timeout=3) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def comfy_submit(host: str, workflow: dict) -> str:
    req = urllib.request.Request(
        host + "/prompt",
        data=json.dumps({"prompt": workflow, "client_id": "continuum-video"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["prompt_id"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"ComfyUI POST /prompt: HTTP {e.code} {e.read().decode()[:300]}") from e


def comfy_wait(host: str, prompt_id: str, timeout_s: float = 600.0) -> tuple[str, str]:
    """Wait for a ComfyUI job. Returns (filename, subfolder)."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(3)
        try:
            with urllib.request.urlopen(f"{host}/history/{prompt_id}", timeout=10) as r:
                h = json.load(r)
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            continue
        if prompt_id in h:
            entry = h[prompt_id]
            st = entry.get("status", {})
            if st.get("status_str") == "error":
                for m in st.get("messages", []):
                    if m[0] == "execution_error":
                        raise RuntimeError(m[1].get("exception_message", "comfy job failed")[:300])
                raise RuntimeError("comfy job failed")
            if st.get("status_str") == "success":
                for out in entry.get("outputs", {}).values():
                    for img in out.get("images", []):
                        return img["filename"], img.get("subfolder", "")
                raise RuntimeError("comfy job finished without output image")
    raise RuntimeError(f"ComfyUI poll timeout for {prompt_id}")


def make_workflow(base_image: str, text: str, negative: str, seed: int,
                  width: int, height: int, steps: int, cfg: float,
                  checkpoint: str, lora: str | None, prefix: str) -> dict:
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "2": {"class_type": "LoadImage", "inputs": {"image": base_image}},
        "11": {"class_type": "ImageScale", "inputs": {"image": ["2", 0], "upscale_method": "lanczos", "width": width, "height": height, "crop": "disabled"}},
        "4": {"class_type": "VAEEncode", "inputs": {"pixels": ["11", 0], "vae": ["1", 2]}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "normal", "denoise": 0.5, "model": ["3", 0], "positive": ["7", 0], "negative": ["8", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 1], "text": text}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 1], "text": negative}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": prefix}},
    }
    if lora:
        wf["3"] = {"class_type": "LoraLoader", "inputs": {"model": ["1", 0], "clip": ["1", 1], "lora_name": lora, "strength_model": 0.5, "strength_clip": 0.5}}
    else:
        wf["3"] = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}}
        wf["7"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": text}}
        wf["8"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": negative}}
    return wf


def prepare_input_image(base_image: pathlib.Path) -> str:
    """Copy base image into the ComfyUI input dir so LoadImage can find it. Returns the filename."""
    root = find_comfy_root()
    if root:
        input_dir = root / "input"
        if input_dir.exists():
            try:
                target = input_dir / base_image.name
                if target.resolve() != base_image.resolve():
                    shutil.copy2(base_image, target)
                return base_image.name
            except OSError:
                pass
    return base_image.name


def generate_frames(host: str, base_image: str, prompt: str, negative: str, seed: int,
                    width: int, height: int, steps: int, cfg: float,
                    frames: int, checkpoint: str, lora: str | None, out_dir: pathlib.Path) -> list[pathlib.Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    image_name = prepare_input_image(pathlib.Path(base_image))
    # Extend the showcase choreography to `frames` entries
    angle_seq = [ANGLES[i % len(ANGLES)] for i in range(frames)]
    style = (f"{prompt.strip()}, cyber-tech neon glow, holographic game UI elements in the background, "
             "dramatic rim lighting, highly detailed, realistic photography, sharp focus")
    paths = []
    for i, (name, angle_text) in enumerate(angle_seq, 1):
        text = f"{style}, {angle_text}"
        pid = comfy_submit(host, make_workflow(image_name, text, negative, seed, width, height, steps, cfg, checkpoint, lora, "continuum/video_frame"))
        filename, subfolder = comfy_wait(host, pid)
        dst = out_dir / f"frame_{i:02d}_{name}.png"
        view = f"{host}/view?filename={urllib.parse.quote(filename)}&subfolder={urllib.parse.quote(subfolder)}&type=output"
        urllib.request.urlretrieve(view, dst)
        paths.append(dst)
    return paths


def build_video(frames: list[pathlib.Path], fps: int, output: pathlib.Path, width: int, height: int) -> float:
    """Ken-Burns stitch: zoompan per frame + xfade crossfades. Returns duration."""
    output.parent.mkdir(parents=True, exist_ok=True)
    n = len(frames)
    if n == 0:
        raise RuntimeError("no frames to stitch")
    inputs = []
    for f in frames:
        inputs += ["-i", str(f)]
    seg = fps  # one second per frame
    fc = []
    for i in range(n):
        fc.append(f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
                  f"zoompan=z='min(zoom+0.002,1.06)':d={seg}:s={width}x{height}:fps={fps},setsar=1[v{i}]")
    if n == 1:
        fc.append("[v0]format=yuv420p[vout]")
    else:
        fade = 0.25
        offset_step = seg / fps - fade  # 1.0 - 0.25 = 0.75
        prev_label = "v0"
        for i in range(1, n):
            out_label = f"x{i}" if i < n - 1 else "vout"
            fc.append(f"[{prev_label}][v{i}]xfade=transition=fade:duration={fade}:offset={round(offset_step * i, 3)}[{out_label}]")
            prev_label = out_label
    filter_complex = ";".join(fc)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs,
           "-filter_complex", filter_complex, "-map", "[vout]", "-r", str(fps),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-movflags", "+faststart", str(output)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(output)],
                           check=True, capture_output=True, text=True)
    try:
        return float(probe.stdout.strip())
    except ValueError:
        return 0.0


def resolve_base_images(args) -> list[pathlib.Path]:
    """Resolve --base-images (comma-separated, bevorzugt) bzw. --base-image zu einer Pfad-Liste."""
    if args.base_images:
        raw = [p.strip() for p in args.base_images.split(",") if p.strip()]
    elif args.base_image:
        raw = [args.base_image]
    else:
        return []
    bases = [pathlib.Path(p) for p in raw]
    missing = [str(b) for b in bases if not b.exists()]
    if missing:
        raise FileNotFoundError(f"base image not found: {', '.join(missing)}")
    return bases


def parse_args():
    ap = argparse.ArgumentParser(description="Animate base frame(s) into 720p video (realistic-video recipe)")
    ap.add_argument("--base-image", default=None, help="Path to single base frame PNG/JPG")
    ap.add_argument("--base-images", default=None, help="Comma-separated list of base images (multi-image bRoll) - bevorzugt gegenueber --base-image")
    ap.add_argument("--prompt", default="full body character showcase, 360 degree turn", help="Motion/choreography prompt")
    ap.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE)
    ap.add_argument("--width", type=int, default=576)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--steps", type=int, default=25)
    ap.add_argument("--cfg", type=float, default=7.0)
    ap.add_argument("--seed", type=int, default=177013)
    ap.add_argument("--frames", type=int, default=6)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--model", choices=["auto", "minimax-h3", "zimage-turbo", "ken-burns"], default="auto")
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    ap.add_argument("--lora", default=DEFAULT_LORA, help="ComfyUI LoRA name or 'none'")
    ap.add_argument("--fallback", choices=["ken-burns"], default="ken-burns")
    ap.add_argument("--sequential", dest="sequential", action="store_true", default=True)
    ap.add_argument("--no-sequential", dest="sequential", action="store_false")
    ap.add_argument("--output", default=None, help="Output mp4 path (default data/videos/<seed>/turn_video.mp4)")
    ap.add_argument("--comfy-host", default=DEFAULT_COMFY_HOST)
    ap.add_argument("--dry-run", action="store_true", help="Validate args without generating")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    try:
        bases = resolve_base_images(args)
    except FileNotFoundError as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1
    if not bases:
        print(json.dumps({"success": False, "error": "need --base-image or --base-images"}))
        return 1
    if args.frames < 1:
        print(json.dumps({"success": False, "error": "frames must be >= 1"}))
        return 1

    lora = None if args.lora.lower() in ("none", "null", "") else args.lora

    model = args.model
    used_model = "ken-burns"
    note = None
    if model in ("minimax-h3", "zimage-turbo"):
        available, found = model_files_available(model)
        if available:
            used_model = model
            note = f"model files present ({len(found)}) but dedicated video workflow not wired yet - using ken-burns"
        else:
            note = f"{model} model files not found in ComfyUI - falling back to {args.fallback}"

    if args.dry_run:
        print(json.dumps({
            "success": True,
            "videoPath": str(bases[0]),
            "images": len(bases),
            "frames": args.frames * len(bases),
            "model": used_model,
            "note": note or "dry run - no frames generated",
            "dryRun": True,
        }))
        return 0

    if used_model == "ken-burns" and not comfy_host_alive(args.comfy_host):
        print(json.dumps({"success": False, "error": f"ComfyUI not reachable at {args.comfy_host}", "model": used_model}))
        return 1

    out_dir = pathlib.Path(args.output).parent if args.output else (REPO_ROOT / "data" / "videos" / str(args.seed))
    all_frames: list[pathlib.Path] = []
    for i, base in enumerate(bases, 1):
        frames = generate_frames(
            args.comfy_host, str(base), args.prompt, args.negative_prompt, args.seed,
            args.width, args.height, args.steps, args.cfg, args.frames,
            args.checkpoint, lora, out_dir / "frames" / f"img{i}",
        )
        all_frames.extend(frames)
    output = pathlib.Path(args.output) if args.output else (out_dir / "turn_video.mp4")
    duration = build_video(all_frames, args.fps, output, args.width, args.height)

    print(json.dumps({
        "success": True,
        "videoPath": str(output),
        "images": len(bases),
        "frames": len(all_frames),
        "model": used_model,
        "duration": round(duration, 3),
        "note": note,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
