import { describe, test, expect } from 'vitest';

describe('realistic recipes', () => {
  test('realistic-image recipe exists and pipeline[2] is image/generate-realistic', async () => {
    const recipe = await import('../../system/recipes/realistic-image.json');
    const data = (recipe as any).default ?? recipe;
    expect(data.uniqueId).toBe('realistic-image');
    expect(data.pipeline[2].command).toBe('image/generate-realistic');
    expect(data.pipeline[2].params.width).toBe(576);
    expect(data.pipeline[2].params.height).toBe(1024);
    expect(data.pipeline[2].params.steps).toBe(25);
  });

  test('realistic-video recipe exists and has image + video steps', async () => {
    const recipe = await import('../../system/recipes/realistic-video.json');
    const data = (recipe as any).default ?? recipe;
    expect(data.uniqueId).toBe('realistic-video');
    const cmds = data.pipeline.map((s: any) => s.command);
    expect(cmds).toContain('image/generate-realistic');
    expect(cmds).toContain('video/generate');
  });

  test('money-printer-realistic recipe exists and has full pipeline', async () => {
    const recipe = await import('../../system/recipes/money-printer-realistic.json');
    const data = (recipe as any).default ?? recipe;
    expect(data.uniqueId).toBe('money-printer-realistic');
    const cmds = data.pipeline.map((s: any) => s.command);
    expect(cmds).toContain('ai/generate');
    expect(cmds).toContain('tts/speak');
    expect(cmds).toContain('image/generate-realistic');
    expect(cmds).toContain('ffmpeg_tiktok');
    expect(cmds).toContain('artifacts/store');
    expect(cmds).toContain('youtube/upload');
  });
});
