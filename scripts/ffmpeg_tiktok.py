#!/usr/bin/env python3
"""ffmpeg_tiktok helper - 1080x1920 9:16 TikTok-Export mit Untertiteln.

Usage:
  python scripts/ffmpeg_tiktok.py --images img1.png,img2.png --audio data/audio/voice.wav
  python scripts/ffmpeg_tiktok.py --video data/media/broll.mp4 --audio data/audio/voice.wav --subtitles
  python scripts/ffmpeg_tiktok.py --images ... --audio ... --subtitles --subtitle-text "Fallback Text"

Prints JSON:
  {"success": true, "videoPath": "...", "width": 1080, "height": 1920, "fps": 24,
   "duration": 6.5, "codecVideo": "h264", "codecAudio": "aac", "subtitlePath": "..."}
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).parent.parent

FALLBACK_SUBTITLE_FONT = "Arial"


def parse_args():
    ap = argparse.ArgumentParser(description="Build 1080x1920 TikTok video with subtitles")
    ap.add_argument("--images", default=None, help="Comma-separated image paths (slideshow base)")
    ap.add_argument("--audio", required=True, help="Audio file (voiceover)")
    ap.add_argument("--video", default=None, help="Optional bRoll video to use instead of slideshow")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--subtitles", action="store_true", help="Burn subtitles from audio transcription")
    ap.add_argument("--subtitle-lang", default="de")
    ap.add_argument("--subtitle-model", default="small")
    ap.add_argument("--subtitle-text", default=None, help="Fallback subtitle text if transcription fails")
    ap.add_argument("--output", default=None, help="Output path (default data/media/tiktok.mp4)")
    ap.add_argument("--dry-run", action="store_true", help="Validate args without rendering")
    return ap.parse_args()


def ffprobe_duration(path: pathlib.Path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def _ts(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _chunk_words(words) -> list[tuple[str, float, float]]:
    """Gruppiert Wort-Timestamps zu Sätzen (an Satzzeichen trennen) wie MoneyPrinterTurbo."""
    chunks: list[tuple[str, float, float]] = []
    cur: list[str] = []
    start = 0.0
    end = 0.0
    for w in words:
        text = (w.word or "").strip()
        if not text:
            continue
        if not cur:
            start = w.start
        cur.append(text)
        end = w.end
        if re.search(r"[.!?…„“]$", text):
            sentence = " ".join(cur).strip()
            if sentence:
                chunks.append((sentence, start, end))
            cur = []
    if cur:
        sentence = " ".join(cur).strip()
        if sentence:
            chunks.append((sentence, start, end))
    return chunks


def transcribe_srt(audio: pathlib.Path, out_dir: pathlib.Path, lang: str, model_size: str) -> pathlib.Path | None:
    """Erzeugt eine SRT-Datei via faster-whisper. None wenn keine Einträge."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        str(audio), language=lang, word_timestamps=True, vad_filter=True, beam_size=5
    )
    entries: list[tuple[float, float, str]] = []
    for seg in segments:
        for text, start, end in _chunk_words(list(getattr(seg, "words", None) or [])):
            if text:
                entries.append((start, end, text))
    if not entries:
        return None
    dst = out_dir / f"{audio.stem}.srt"
    lines: list[str] = []
    for i, (start, end, text) in enumerate(entries, 1):
        lines.append(str(i))
        lines.append(f"{_ts(start)} --> {_ts(end)}")
        lines.append(text)
        lines.append("")
    dst.write_text("\n".join(lines), encoding="utf-8")
    return dst


def fallback_srt(text: str, duration: float, out_dir: pathlib.Path) -> pathlib.Path:
    """Einzel-Eintrag-SRT über die volle Dauer als Fallback."""
    dst = out_dir / "fallback.srt"
    dst.write_text(
        f"1\n{_ts(0.2)} --> {_ts(max(duration - 0.2, 0.3))}\n{text}\n", encoding="utf-8"
    )
    return dst


def escape_filter_path(p: pathlib.Path) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def build_slideshow(images: list[pathlib.Path], duration: float, width: int, height: int,
                    fps: int, out: pathlib.Path) -> pathlib.Path:
    """Ken-Burns-Slideshow: zoompan pro Bild + xfade-Fades. Returns video path."""
    n = len(images)
    fade = min(0.6, duration / n / 4)
    seg = (duration + fade * (n - 1)) / n
    inputs: list[str] = []
    filters: list[str] = []
    last = ""
    for i, img in enumerate(images, 1):
        inputs += ["-loop", "1", "-t", f"{seg:.3f}", "-i", str(img)]
        filters.append(
            f"[{i - 1}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},zoompan=z='min(zoom+0.002,1.06)':d=1:"
            f"s={width}x{height}:fps={fps},setsar=1,trim=duration={seg:.3f},"
            f"setpts=PTS-STARTPTS[v{i}]"
        )
        if i == 1:
            last = "[v1]"
        else:
            offset = round((i - 1) * (seg - fade), 3)
            out_label = f"[vx{i}]"
            filters.append(f"{last}[v{i}]xfade=transition=fade:duration={fade:.3f}:offset={offset}{out_label}")
            last = out_label
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs,
        "-filter_complex", ";".join(filters), "-map", last,
        "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-r", str(fps),
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"slideshow failed: {result.stderr[-2000:]}")
    return out


def fit_video(src: pathlib.Path, width: int, height: int, out: pathlib.Path) -> pathlib.Path:
    """Skaliert/croppt das bRoll-Video auf exakt width x height (9:16)."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
           "-vf", (f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                   f"crop={width}:{height},setsar=1"),
           "-c:v", "libx264", "-crf", "20", "-preset", "fast",
           "-c:a", "copy", str(out)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"fit failed: {result.stderr[-2000:]}")
    return out


def mux_audio(video: pathlib.Path, audio: pathlib.Path, duration: float,
              out: pathlib.Path) -> pathlib.Path:
    """Hängt den Voiceover an und begrenzt die Länge auf die Audio-Dauer."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-stream_loop", "-1", "-i", str(video), "-i", str(audio),
           "-map", "0:v:0", "-map", "1:a:0", "-t", f"{duration:.3f}",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", str(out)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"mux failed: {result.stderr[-2000:]}")
    return out


def burn_subtitles(video: pathlib.Path, srt: pathlib.Path, out: pathlib.Path) -> pathlib.Path:
    srt_esc = escape_filter_path(srt)
    vf = (
        f"subtitles='{srt_esc}':force_style="
        f"'FontName={FALLBACK_SUBTITLE_FONT},FontSize=22,PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H80000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=80'"
    )
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video),
           "-vf", vf, "-c:v", "libx264", "-crf", "20", "-preset", "fast",
           "-c:a", "copy", "-movflags", "+faststart", str(out)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"subtitles failed: {result.stderr[-2000:]}")
    return out


def main() -> int:
    args = parse_args()
    audio = pathlib.Path(args.audio)
    if not audio.exists():
        print(json.dumps({"success": False, "error": f"audio not found: {audio}"}))
        return 1
    out = pathlib.Path(args.output) if args.output else (REPO_ROOT / "data" / "media" / "tiktok.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / "tiktok_work"
    work.mkdir(parents=True, exist_ok=True)

    duration = 0.0 if args.dry_run else ffprobe_duration(audio)
    if duration <= 0:
        print(json.dumps({"success": False, "error": "could not probe audio duration"}))
        return 1

    images = [pathlib.Path(p.strip()) for p in args.images.split(",")] if args.images else []
    images = [p for p in images if p.exists()]
    if not images and not args.video:
        print(json.dumps({"success": False, "error": "need --images or --video"}))
        return 1

    if args.dry_run:
        print(json.dumps({
            "success": True, "dryRun": True, "audio": str(audio), "duration": duration,
            "images": [str(p) for p in images], "video": args.video,
            "subtitles": bool(args.subtitles), "output": str(out),
        }))
        return 0

    # 1. Basisvideo: bRoll oder Ken-Burns-Slideshow
    if args.video:
        broll = pathlib.Path(args.video)
        if not broll.exists():
            print(json.dumps({"success": False, "error": f"video not found: {broll}"}))
            return 1
        base = fit_video(broll, args.width, args.height, work / "base.mp4")
    else:
        base = build_slideshow(images, duration, args.width, args.height, args.fps,
                               work / "slideshow.mp4")

    # 2. Audio muxen (Video auf Audio-Dauer begrenzen)
    muxed = mux_audio(base, audio, duration, work / "muxed.mp4")

    # 3. Untertitel
    subtitle_path = None
    if args.subtitles:
        srt = transcribe_srt(audio, work, args.subtitle_lang, args.subtitle_model)
        if srt is None and args.subtitle_text:
            srt = fallback_srt(args.subtitle_text, duration, work)
        if srt is not None:
            subtitle_path = srt
            burn_subtitles(muxed, srt, out)
        else:
            muxed.rename(out) if muxed != out else None
    else:
        muxed.rename(out) if muxed != out else None

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height,r_frame_rate",
         "-of", "json", str(out)],
        capture_output=True, text=True, check=True,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    print(json.dumps({
        "success": True, "videoPath": str(out),
        "width": stream.get("width"), "height": stream.get("height"),
        "fps": args.fps, "duration": round(duration, 3),
        "codecVideo": stream.get("codec_name"), "codecAudio": "aac",
        "subtitlePath": str(subtitle_path) if subtitle_path else None,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
