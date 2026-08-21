import { describe, test, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { spawn } from 'child_process';

async function ffprobeDimensions(filePath: string): Promise<{ width: number; height: number; codecVideo: string; codecAudio: string }> {
  return new Promise((resolve, reject) => {
    const args = ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,codec_name', '-of', 'json', filePath];
    const p = spawn('ffprobe', args);
    let out = '';
    let err = '';
    p.stdout.on('data', (d) => (out += d.toString()));
    p.stderr.on('data', (d) => (err += d.toString()));
    p.on('close', (code) => {
      if (code !== 0) return reject(new Error(`ffprobe video failed ${code} ${err} ${out}`));
      try {
        const j = JSON.parse(out);
        const stream = j.streams?.[0] ?? {};
        const width = parseInt(String(stream.width), 10);
        const height = parseInt(String(stream.height), 10);
        const codecVideo = String(stream.codec_name ?? '');
        const aProbe = spawn('ffprobe', ['-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_name', '-of', 'json', filePath]);
        let aOut = '';
        let aErr = '';
        aProbe.stdout.on('data', (d) => (aOut += d.toString()));
        aProbe.stderr.on('data', (d) => (aErr += d.toString()));
        aProbe.on('close', (aCode) => {
          try {
            const aj = JSON.parse(aOut);
            const aStream = aj.streams?.[0] ?? {};
            const audioCodec = String(aStream.codec_name ?? '');
            resolve({ width, height, codecVideo, codecAudio: audioCodec });
          } catch {
            resolve({ width, height, codecVideo, codecAudio: '' });
          }
        });
        aProbe.on('error', () => resolve({ width, height, codecVideo, codecAudio: '' }));
      } catch (e) {
        reject(new Error(`ffprobe parse failed: ${e} out=${out} err=${err}`));
      }
    });
    p.on('error', reject);
  });
}

describe('money-printer E2E (TTS+ffmpeg)', () => {
  test('recipe money-printer-realistic exists with ffmpeg_tiktok 1080x1920', async () => {
    const recipe = await import('../../system/recipes/money-printer-realistic.json');
    const data = (recipe as any).default ?? recipe;
    expect(data.uniqueId).toBe('money-printer-realistic');
    const cmds = data.pipeline.map((s: any) => s.command);
    expect(cmds).toContain('ffmpeg_tiktok');
    const tiktokStep = data.pipeline.find((s: any) => s.command === 'ffmpeg_tiktok');
    expect(tiktokStep.params.width).toBe(1080);
    expect(tiktokStep.params.height).toBe(1920);
    expect(tiktokStep.params.fps).toBe(24);
    expect(tiktokStep.params.subtitles).toBe(true);
  });

  test('money-printer produces 1080x1920 mp4 with prompt "a cozy cafe" (mocked ComfyUI/Kokoro)', async () => {
    const { ffmpegTiktok } = await import('../../commands/media/ffmpeg-tiktok/shared/FFmpegTiktokTypes.js');
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'money-printer-'));
    const outPath = path.join(tmpDir, 'tiktok.mp4');
    const res = await ffmpegTiktok({
      prompt: 'a cozy cafe',
      width: 1080,
      height: 1920,
      fps: 24,
      subtitles: true,
      subtitleModel: 'small',
      subtitleLang: 'de',
      outputPath: outPath,
    } as any);

    expect(res.success).toBe(true);
    expect(res.videoPath).toMatch(/\.mp4$/);
    expect(fs.existsSync(res.videoPath!)).toBe(true);

    const dims = await ffprobeDimensions(res.videoPath!);
    expect(dims.width).toBe(1080);
    expect(dims.height).toBe(1920);
    expect(dims.codecVideo).toMatch(/h264/);
    expect(dims.codecAudio).toMatch(/aac/);

    expect(fs.statSync(res.videoPath!).size).toBeGreaterThan(1000);
  }, 60000);

  test('ffmpeg_tiktok module is importable via top-level shim', async () => {
    const mod = await import('../../commands/media/ffmpeg-tiktok.js');
    expect(mod).toBeDefined();
    expect(mod.ffmpegTiktok).toBeDefined();
  });
});
