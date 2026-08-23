import type { CommandParams, JTAGPayload, CommandInput } from '../../../../system/core/types/JTAGTypes';
import * as fs from 'fs';
import * as path from 'path';
import { execFile } from 'child_process';

export interface VideoGenerateParams extends CommandParams {
  prompt?: string;
  baseImage?: string | string[];
  baseFrame?: string | string[];
  negativePrompt?: string;
  width?: number;
  height?: number;
  steps?: number;
  cfg?: number;
  seed?: number;
  frames?: number;
  fps?: number;
  model?: 'auto' | 'minimax-h3' | 'zimage-turbo' | 'ken-burns';
  checkpoint?: string;
  lora?: string;
  sequential?: boolean;
  fallback?: 'ken-burns';
  outputDir?: string;
}

export interface VideoGenerateResult extends JTAGPayload {
  success: boolean;
  videoPath?: string;
  frames?: number;
  model?: string;
  duration?: number;
  error?: string;
}

export function createVideoGenerateResult(params: VideoGenerateParams, outcome: Partial<VideoGenerateResult>): VideoGenerateResult {
  return {
    success: outcome.success ?? false,
    videoPath: outcome.videoPath,
    frames: outcome.frames,
    model: outcome.model,
    duration: outcome.duration,
    error: outcome.error,
    context: params.context,
    sessionId: params.sessionId,
  };
}

function firstImage(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

export function resolveVideoGenerateParams(params: VideoGenerateParams): VideoGenerateParams {
  return {
    ...params,
    prompt: params.prompt ?? firstImage(params.baseFrame) ?? 'full body character showcase, 360 degree turn',
    baseImage: firstImage(params.baseImage) ?? firstImage(params.baseFrame),
    negativePrompt: params.negativePrompt ?? 'blurry, low quality, distorted, deformed, bad anatomy',
    width: params.width ?? 576,
    height: params.height ?? 1024,
    steps: params.steps ?? 25,
    cfg: params.cfg ?? 7,
    seed: params.seed ?? Math.floor(Math.random() * 1000000000),
    frames: params.frames ?? 6,
    fps: params.fps ?? 24,
    model: params.model ?? 'auto',
    fallback: params.fallback ?? 'ken-burns',
  };
}

function findHelperScript(): string | null {
  const candidates = [
    path.resolve(process.cwd(), 'scripts', 'video_generate.py'),
    path.resolve(__dirname, '../../../../../scripts/video_generate.py'),
    'C:/OmniRoute/repos/continuum/scripts/video_generate.py',
  ];
  for (const p of candidates) {
    try {
      if (fs.existsSync(p) && fs.statSync(p).isFile()) return p;
    } catch {}
  }
  return null;
}

export async function generateVideo(params: VideoGenerateParams): Promise<VideoGenerateResult> {
  const resolved = resolveVideoGenerateParams(params);
  // Rezept uebergibt baseImage als Array ($generatedImages) -> alle Bilder durchreichen.
  const rawImages = Array.isArray(params.baseImage) ? params.baseImage : (params.baseImage ? [params.baseImage] : []);
  const baseImages = rawImages.map((p) => path.resolve(p)).filter((p) => fs.existsSync(p));

  if (baseImages.length === 0) {
    return createVideoGenerateResult(params, {
      success: false,
      error: `base image not found: ${rawImages.join(', ') ?? 'undefined'} - run image/generate-realistic first`,
    });
  }

  const helper = findHelperScript();
  if (!helper) {
    return createVideoGenerateResult(params, {
      success: false,
      error: 'scripts/video_generate.py not found - continuum repo incomplete',
    });
  }

  const args = [
    helper,
    ...(baseImages.length > 1
      ? ['--base-images', baseImages.join(',')]
      : ['--base-image', baseImages[0]]),
    '--prompt', resolved.prompt ?? '',
    '--negative-prompt', resolved.negativePrompt ?? '',
    '--width', String(resolved.width),
    '--height', String(resolved.height),
    '--steps', String(resolved.steps),
    '--cfg', String(resolved.cfg),
    '--seed', String(resolved.seed),
    '--frames', String(resolved.frames),
    '--fps', String(resolved.fps),
    '--model', resolved.model ?? 'auto',
    '--fallback', resolved.fallback ?? 'ken-burns',
  ];
  if (resolved.checkpoint) args.push('--checkpoint', resolved.checkpoint);
  if (resolved.lora) args.push('--lora', resolved.lora);
  if (resolved.outputDir) args.push('--output', resolved.outputDir);
  if (resolved.sequential === false) args.push('--no-sequential');

  try {
    const stdout = await runPython(helper, args);
    const data = JSON.parse(stdout) as VideoGenerateResult;
    return createVideoGenerateResult(params, data);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return createVideoGenerateResult(params, {
      success: false,
      error: `video_generate.py failed: ${msg}`,
    });
  }
}

function runPython(helper: string, args: string[]): Promise<string> {
  return new Promise((resolvePromise, reject) => {
    execFile('python', args, { cwd: path.resolve(helper, '../..'), timeout: 600000, maxBuffer: 8 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) {
        const detail = stderr ? `\n${stderr.toString().slice(0, 800)}` : '';
        reject(new Error(`${error.message}${detail}`));
        return;
      }
      resolvePromise(stdout.toString());
    });
  });
}

export const VideoGenerate = {
  async execute(params: CommandInput<VideoGenerateParams>): Promise<VideoGenerateResult> {
    const { Commands } = await import('../../../../system/core/shared/Commands');
    return Commands.execute<VideoGenerateParams, VideoGenerateResult>('video/generate', params as Partial<VideoGenerateParams>);
  },
  commandName: 'video/generate' as const,
} as const;
