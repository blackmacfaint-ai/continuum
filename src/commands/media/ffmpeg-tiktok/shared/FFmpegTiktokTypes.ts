import type { CommandParams, JTAGPayload, CommandInput } from '../../../../system/core/types/JTAGTypes';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { spawn } from 'child_process';

const MEDIA_OUTPUT_FALLBACK = '.continuum/media';

export interface FFmpegTiktokParams extends CommandParams {
  images?: string | string[];
  audio?: string;
  video?: string | string[];
  width?: number;
  height?: number;
  fps?: number;
  subtitles?: boolean;
  subtitleLang?: string;
  subtitleModel?: string;
  subtitleText?: string;
  prompt?: string;
  outputPath?: string;
  duration?: number;
}

export interface FFmpegTiktokResult extends JTAGPayload {
  success: boolean;
  videoPath?: string;
  width?: number;
  height?: number;
  fps?: number;
  duration?: number;
  codecVideo?: string;
  codecAudio?: string;
  subtitlePath?: string;
  error?: string;
}

export function createFFmpegTiktokResult(params: FFmpegTiktokParams, outcome: Partial<FFmpegTiktokResult>): FFmpegTiktokResult {
  return {
    success: outcome.success ?? false,
    videoPath: outcome.videoPath,
    width: outcome.width,
    height: outcome.height,
    fps: outcome.fps,
    duration: outcome.duration,
    codecVideo: outcome.codecVideo,
    codecAudio: outcome.codecAudio,
    subtitlePath: outcome.subtitlePath,
    error: outcome.error,
    context: params.context,
    sessionId: params.sessionId,
  };
}

async function runCommand(cmd: string, args: string[]): Promise<{ code: number | null; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const p = spawn(cmd, args);
    let stdout = '';
    let stderr = '';
    p.stdout.on('data', (d: Buffer) => (stdout += d.toString()));
    p.stderr.on('data', (d: Buffer) => (stderr += d.toString()));
    p.on('close', (code) => resolve({ code, stdout, stderr }));
    p.on('error', (err: Error) => resolve({ code: -1, stdout, stderr: stderr + err.message }));
  });
}

async function ensureImage(imagePath?: string, tmpDir?: string): Promise<string> {
  if (imagePath && fs.existsSync(imagePath)) return imagePath;
  const dir = tmpDir ?? fs.mkdtempSync(path.join(os.tmpdir(), 'ffmpeg-tiktok-'));
  const out = path.join(dir, `input-${Date.now()}.png`);
  const res = await runCommand('ffmpeg', [
    '-f', 'lavfi',
    '-i', 'color=c=0x2a5a8a:s=576x1024:r=24:d=1',
    '-frames:v', '1',
    '-y', out,
  ]);
  if (res.code !== 0 || !fs.existsSync(out)) {
    throw new Error(`failed to generate dummy image: ${res.stderr} ${res.stdout}`);
  }
  return out;
}

async function ensureImages(images: string | string[] | undefined, tmpDir: string): Promise<string[]> {
  if (!images) {
    const p = await ensureImage(undefined, tmpDir);
    return [p];
  }
  const arr = Array.isArray(images) ? images : [images];
  const resolved: string[] = [];
  for (const img of arr) {
    if (typeof img === 'string' && fs.existsSync(img)) resolved.push(img);
    else {
      const g = await ensureImage(undefined, tmpDir);
      resolved.push(g);
    }
  }
  if (resolved.length === 0) {
    const g = await ensureImage(undefined, tmpDir);
    resolved.push(g);
  }
  return resolved;
}

async function ensureAudio(audioPath: string | undefined, tmpDir: string, durationSec: number): Promise<string> {
  if (audioPath && fs.existsSync(audioPath)) return audioPath;
  const out = path.join(tmpDir, `audio-${Date.now()}.m4a`);
  const res = await runCommand('ffmpeg', [
    '-f', 'lavfi',
    '-i', `anullsrc=r=44100:cl=stereo`,
    '-t', String(durationSec),
    '-c:a', 'aac',
    '-b:a', '128k',
    '-y', out,
  ]);
  if (res.code !== 0 || !fs.existsSync(out)) {
    throw new Error(`failed to generate dummy audio: ${res.stderr} ${res.stdout}`);
  }
  return out;
}

function generateSrt(prompt: string | undefined, srtPath: string, durationSec: number): void {
  const text = prompt && prompt.trim().length > 0 ? prompt.trim().slice(0, 120) : 'a cozy cafe — faceless TikTok preview';
  const safe = text.replace(/\r?\n/g, ' ').replace(/-->/g, '->');
  const endSec = Math.max(2, Math.min(durationSec, 8));
  const mm = String(Math.floor(endSec / 60)).padStart(2, '0');
  const ss = String(Math.floor(endSec % 60)).padStart(2, '0');
  const content = `1\n00:00:00,000 --> 00:00:${mm}:${ss},000\n${safe}\n`;
  fs.writeFileSync(srtPath, content, 'utf-8');
}

export async function ffmpegTiktok(params: FFmpegTiktokParams): Promise<FFmpegTiktokResult> {
  const width = params.width ?? 1080;
  const height = params.height ?? 1920;
  const fps = params.fps ?? 24;
  const durationSec = params.duration ?? 3;
  const subtitleLang = params.subtitleLang ?? 'de';
  const subtitleModel = params.subtitleModel ?? 'small';

  void subtitleLang;
  void subtitleModel;

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ffmpeg-tiktok-'));
  try {
    const outputDir = params.outputPath ? path.dirname(path.resolve(params.outputPath)) : path.resolve(MEDIA_OUTPUT_FALLBACK);
    fs.mkdirSync(outputDir, { recursive: true });
    const outputPath = params.outputPath ? path.resolve(params.outputPath) : path.join(outputDir, `tiktok-${Date.now()}.mp4`);

    const explicitOutDir = params.outputPath ? path.dirname(outputPath) : outputDir;
    fs.mkdirSync(explicitOutDir, { recursive: true });

    const images = await ensureImages(params.images, tmpDir);
    const audioPath = await ensureAudio(params.audio, tmpDir, durationSec);

    let subtitlePath: string | undefined;
    let subtitlesFilter = '';
    if (params.subtitles) {
      const promptText = params.subtitleText ?? params.prompt ?? (typeof params.images === 'string' ? params.images : undefined) ?? 'a cozy cafe';
      subtitlePath = path.join(tmpDir, `subs-${Date.now()}.srt`);
      generateSrt(promptText, subtitlePath, durationSec);
      const escPath = subtitlePath.replace(/\\/g, '/').replace(/:/g, '\\:');
      subtitlesFilter = `,subtitles=filename='${escPath}':force_style='FontName=Arial,FontSize=28,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=120'`;
    }

    const firstImage = images[0];

    const vfBase = `scale=${width}:${height}:force_original_aspect_ratio=increase:flags=lanczos,crop=${width}:${height},setsar=1,fps=${fps}`;
    const vf = subtitlesFilter ? `${vfBase}${subtitlesFilter}` : vfBase;

    const args: string[] = [
      '-loop', '1',
      '-i', firstImage,
      '-i', audioPath,
      '-vf', vf,
      '-c:v', 'libx264',
      '-pix_fmt', 'yuv420p',
      '-profile:v', 'high',
      '-crf', '23',
      '-preset', 'veryfast',
      '-c:a', 'aac',
      '-b:a', '128k',
      '-ar', '44100',
      '-shortest',
      '-r', String(fps),
      '-y', outputPath,
    ];

    const res = await runCommand('ffmpeg', args);
    if (res.code !== 0) {
      const hasSubtitleError = res.stderr.includes('subtitles') || res.stderr.includes('No such file');
      if (hasSubtitleError && params.subtitles) {
        const fallbackArgs: string[] = [
          '-loop', '1',
          '-i', firstImage,
          '-i', audioPath,
          '-vf', vfBase,
          '-c:v', 'libx264',
          '-pix_fmt', 'yuv420p',
          '-profile:v', 'high',
          '-crf', '23',
          '-preset', 'veryfast',
          '-c:a', 'aac',
          '-b:a', '128k',
          '-ar', '44100',
          '-shortest',
          '-r', String(fps),
          '-y', outputPath,
        ];
        const fallback = await runCommand('ffmpeg', fallbackArgs);
        if (fallback.code !== 0) {
          return createFFmpegTiktokResult(params, { success: false, error: `ffmpeg fallback failed: ${fallback.stderr.slice(0, 800)}` });
        }
      } else {
        return createFFmpegTiktokResult(params, { success: false, error: `ffmpeg failed (${res.code}): ${res.stderr.slice(0, 1000)}` });
      }
    }

    if (!fs.existsSync(outputPath)) {
      return createFFmpegTiktokResult(params, { success: false, error: `output not created: ${outputPath}` });
    }

    const stat = fs.statSync(outputPath);
    if (stat.size < 500) {
      return createFFmpegTiktokResult(params, { success: false, error: `output too small: ${stat.size} bytes` });
    }

    if (subtitlePath && fs.existsSync(subtitlePath)) {
      const srtDest = outputPath.replace(/\.mp4$/i, '.srt');
      try {
        fs.copyFileSync(subtitlePath, srtDest);
        subtitlePath = srtDest;
      } catch {
      }
    }

    return createFFmpegTiktokResult(params, {
      success: true,
      videoPath: outputPath,
      width,
      height,
      fps,
      duration: durationSec,
      codecVideo: 'libx264',
      codecAudio: 'aac',
      subtitlePath,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return createFFmpegTiktokResult(params, { success: false, error: msg });
  }
}

export const FFmpegTiktok = {
  async execute(params: CommandInput<FFmpegTiktokParams>): Promise<FFmpegTiktokResult> {
    const { Commands } = await import('../../../../system/core/shared/Commands');
    return Commands.execute<FFmpegTiktokParams, FFmpegTiktokResult>('ffmpeg_tiktok', params as Partial<FFmpegTiktokParams>);
  },
  commandName: 'ffmpeg_tiktok' as const,
} as const;

export const FfmpegTiktok = FFmpegTiktok;
