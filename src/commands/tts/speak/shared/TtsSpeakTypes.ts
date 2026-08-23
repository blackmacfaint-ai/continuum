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
  speed?: number;
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

export function resolveTtsSpeakParams(params: TtsSpeakParams): TtsSpeakParams {
  return {
    ...params,
    voice: params.voice ?? 'martin',
    engine: params.engine ?? 'kokoro',
    fallbackEngine: params.fallbackEngine ?? 'voicebox',
    lang: params.lang ?? 'de',
    profile: params.profile ?? 'Overlay DE',
    speed: params.speed ?? 1.5,
  };
}

function findHelper(): string | null {
  const candidates = [
    path.resolve(process.cwd(), 'scripts', 'tts_speak.py'),
    path.resolve(__dirname, '../../../../../scripts/tts_speak.py'),
    'C:/OmniRoute/repos/continuum/scripts/tts_speak.py',
  ];
  for (const p of candidates) {
    try {
      if (fs.existsSync(p) && fs.statSync(p).isFile()) return p;
    } catch {}
  }
  return null;
}

export async function ttsSpeak(params: TtsSpeakParams): Promise<TtsSpeakResult> {
  if (!params.text || !params.text.trim()) {
    return createTtsSpeakResult(params, { success: false, error: 'text is required' });
  }
  const helper = findHelper();
  if (!helper) {
    return createTtsSpeakResult(params, { success: false, error: 'scripts/tts_speak.py not found' });
  }
  const resolved = resolveTtsSpeakParams(params);
  const args = [helper, '--text', resolved.text];
  if (resolved.voice) args.push('--voice', resolved.voice);
  if (resolved.engine) args.push('--engine', resolved.engine);
  if (resolved.fallbackEngine) args.push('--fallback-engine', resolved.fallbackEngine);
  if (resolved.lang) args.push('--lang', resolved.lang);
  if (resolved.profile) args.push('--profile', resolved.profile);
  if (resolved.speed) args.push('--speed', String(resolved.speed));
  if (resolved.output) args.push('--output', resolved.output);
  try {
    const stdout = await runPython(helper, args);
    const data = JSON.parse(stdout) as TtsSpeakResult;
    return createTtsSpeakResult(params, data);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return createTtsSpeakResult(params, { success: false, error: `tts_speak.py failed: ${msg}` });
  }
}

function runPython(helper: string, args: string[]): Promise<string> {
  return new Promise((resolvePromise, reject) => {
    execFile('python', args, { cwd: path.resolve(helper, '../..'), timeout: 120000, maxBuffer: 8 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) {
        const detail = stderr ? `\n${stderr.toString().slice(0, 800)}` : '';
        reject(new Error(`${error.message}${detail}`));
        return;
      }
      resolvePromise(stdout.toString());
    });
  });
}

export const TtsSpeak = {
  async execute(params: CommandInput<TtsSpeakParams>): Promise<TtsSpeakResult> {
    const { Commands } = await import('../../../../system/core/shared/Commands');
    return Commands.execute<TtsSpeakParams, TtsSpeakResult>('tts/speak', params as Partial<TtsSpeakParams>);
  },
  commandName: 'tts/speak' as const,
} as const;
