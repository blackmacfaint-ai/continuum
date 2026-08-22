import { describe, test, expect } from 'vitest';

describe('forge alloy stub', () => {
  test('forge contract exists', async () => {
    const alloy = await import('../../../docs/forge/realistic-vision-lora.json');
    const data = (alloy as any).default ?? alloy;
    expect(data.recipe).toBeDefined();
  });

  test('forge contract targets continuum-ai/realistic-vision-lora and has prun/train/quant/eval', async () => {
    const alloy = await import('../../../docs/forge/realistic-vision-lora.json');
    const data = (alloy as any).default ?? alloy;
    expect(data.model).toBe('continuum-ai/realistic-vision-lora');
    expect(data.base).toContain('realisticVisionV60B1');
    const recipe = data.recipe;
    expect(recipe.prun).toBeDefined();
    expect(recipe.train).toBeDefined();
    expect(recipe.quant).toBeDefined();
    expect(recipe.eval).toBeDefined();
  });
});
