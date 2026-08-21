import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { generateRealistic, resolveComfyUIHost } from './generate-realistic.js';

describe('image/generate-realistic', () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  test('generates 576x1024 PNG', async () => {
    const mockPromptId = 'test-prompt-123';
    const mockFilename = 'continuum_realistic_00001_.png';

    globalThis.fetch = vi.fn(async (url: string | URL | Request, init?: RequestInit) => {
      const u = typeof url === 'string' ? url : url.toString();
      if (u.includes('/system_stats')) {
        return { ok: true, json: async () => ({}), text: async () => '{}', arrayBuffer: async () => new ArrayBuffer(0) } as unknown as Response;
      }
      if (u.endsWith('/prompt') && init?.method === 'POST') {
        const body = JSON.parse(init.body as string);
        expect(body.prompt['3'].inputs.ckpt_name).toBe('realisticVisionV60B1_v51HyperVAE.safetensors');
        expect(body.prompt['4'].inputs.text).toBe('a photo of a cat');
        expect(body.prompt['6'].inputs.width).toBe(576);
        expect(body.prompt['6'].inputs.height).toBe(1024);
        expect(body.prompt['7'].inputs.steps).toBe(5);
        expect(body.prompt['7'].inputs.sampler_name).toBe('euler');
        expect(body.prompt['7'].inputs.cfg).toBe(7);
        expect(body.prompt['9'].class_type).toBe('SaveImage');
        return {
          ok: true,
          json: async () => ({ prompt_id: mockPromptId }),
          text: async () => JSON.stringify({ prompt_id: mockPromptId }),
        } as unknown as Response;
      }
      if (u.includes(`/history/${mockPromptId}`)) {
        return {
          ok: true,
          json: async () => ({
            [mockPromptId]: {
              status: { completed: true },
              outputs: {
                '9': { images: [{ filename: mockFilename, subfolder: '', type: 'output' }] },
              },
            },
          }),
          text: async () => '{}',
        } as unknown as Response;
      }
      if (u.includes('/view')) {
        return {
          ok: true,
          arrayBuffer: async () => new Uint8Array([0x89, 0x50, 0x4e, 0x47]).buffer,
          json: async () => ({}),
          text: async () => '',
        } as unknown as Response;
      }
      return { ok: false, status: 404, json: async () => ({}), text: async () => 'not found', arrayBuffer: async () => new ArrayBuffer(0) } as unknown as Response;
    }) as unknown as typeof fetch;

    const res = await generateRealistic({ prompt: 'a photo of a cat', width: 576, height: 1024, steps: 5 });
    expect(res.imagePath).toMatch(/\.png$/);
    expect(res.prompt).toBe('a photo of a cat');
    expect(typeof res.seed).toBe('number');
  });

  test('resolves host.docker.internal first, fallback to localhost', async () => {
    let firstCalled = false;
    globalThis.fetch = vi.fn(async (url: string | URL | Request) => {
      const u = typeof url === 'string' ? url : url.toString();
      if (u.includes('host.docker.internal')) {
        firstCalled = true;
        return { ok: true, json: async () => ({}), text: async () => '' } as unknown as Response;
      }
      return { ok: true, json: async () => ({}), text: async () => '' } as unknown as Response;
    }) as unknown as typeof fetch;
    const host = await resolveComfyUIHost();
    expect(firstCalled).toBe(true);
    expect(host).toBe('http://host.docker.internal:8188');
  });

  test('fallback to localhost when host.docker.internal fails', async () => {
    globalThis.fetch = vi.fn(async (url: string | URL | Request) => {
      const u = typeof url === 'string' ? url : url.toString();
      if (u.includes('host.docker.internal')) {
        throw new Error('network error');
      }
      if (u.includes('localhost')) {
        return { ok: true, json: async () => ({}), text: async () => '' } as unknown as Response;
      }
      return { ok: false, json: async () => ({}), text: async () => '' } as unknown as Response;
    }) as unknown as typeof fetch;
    const host = await resolveComfyUIHost();
    expect(host).toBe('http://localhost:8188');
  });

  test('throws on missing prompt', async () => {
    await expect(generateRealistic({ prompt: '' })).rejects.toThrow('prompt is required');
  });

  test('uses custom checkpoint and seed', async () => {
    const mockPromptId = 'custom-checkpoint-test';
    globalThis.fetch = vi.fn(async (url: string | URL | Request, init?: RequestInit) => {
      const u = typeof url === 'string' ? url : url.toString();
      if (u.includes('/system_stats')) return { ok: true, json: async () => ({}), text: async () => '' } as unknown as Response;
      if (u.endsWith('/prompt') && init?.method === 'POST') {
        const body = JSON.parse(init.body as string);
        expect(body.prompt['3'].inputs.ckpt_name).toBe('my-custom.safetensors');
        expect(body.prompt['7'].inputs.seed).toBe(42);
        expect(body.prompt['5'].inputs.text).toBe('bad quality');
        return { ok: true, json: async () => ({ prompt_id: mockPromptId }), text: async () => '' } as unknown as Response;
      }
      if (u.includes(`/history/${mockPromptId}`)) {
        return {
          ok: true,
          json: async () => ({
            [mockPromptId]: {
              status: { completed: true },
              outputs: { '9': { images: [{ filename: 'out.png', subfolder: '', type: 'output' }] } },
            },
          }),
          text: async () => '',
        } as unknown as Response;
      }
      if (u.includes('/view')) {
        return { ok: true, arrayBuffer: async () => new ArrayBuffer(8), json: async () => ({}), text: async () => '' } as unknown as Response;
      }
      return { ok: false, json: async () => ({}), text: async () => '' } as unknown as Response;
    }) as unknown as typeof fetch;

    const res = await generateRealistic({
      prompt: 'a dog',
      negativePrompt: 'bad quality',
      checkpoint: 'my-custom.safetensors',
      seed: 42,
    });
    expect(res.seed).toBe(42);
    expect(res.imagePath).toMatch(/\.png$/);
  });
});
