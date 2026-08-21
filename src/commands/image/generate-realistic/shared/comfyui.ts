export type GenerateRealisticParams = {
  prompt: string;
  negativePrompt?: string;
  width?: number;
  height?: number;
  steps?: number;
  cfg?: number;
  seed?: number;
  checkpoint?: string;
};

export type GenerateRealisticResult = {
  imagePath: string;
  seed: number;
  prompt: string;
};

const DEFAULT_CHECKPOINT = 'realisticVisionV60B1_v51HyperVAE.safetensors';
const DEFAULT_WIDTH = 576;
const DEFAULT_HEIGHT = 1024;
const DEFAULT_STEPS = 25;
const DEFAULT_CFG = 7;
const DEFAULT_NEGATIVE = 'blurry, low quality, distorted, deformed';

export async function resolveComfyUIHost(): Promise<string> {
  const candidates = ['http://host.docker.internal:8188', 'http://localhost:8188'];
  for (const host of candidates) {
    try {
      const res = await fetch(`${host}/system_stats`, { method: 'GET' });
      if (res.ok) return host;
    } catch {
    }
  }
  return 'http://localhost:8188';
}

function buildWorkflow(params: GenerateRealisticParams, seed: number) {
  const width = params.width ?? DEFAULT_WIDTH;
  const height = params.height ?? DEFAULT_HEIGHT;
  const steps = params.steps ?? DEFAULT_STEPS;
  const cfg = params.cfg ?? DEFAULT_CFG;
  const checkpoint = params.checkpoint ?? DEFAULT_CHECKPOINT;
  const negativePrompt = params.negativePrompt ?? DEFAULT_NEGATIVE;
  return {
    '3': { class_type: 'CheckpointLoaderSimple', inputs: { ckpt_name: checkpoint } },
    '4': { class_type: 'CLIPTextEncode', inputs: { text: params.prompt, clip: ['3', 1] } },
    '5': { class_type: 'CLIPTextEncode', inputs: { text: negativePrompt, clip: ['3', 1] } },
    '6': { class_type: 'EmptyLatentImage', inputs: { width, height, batch_size: 1 } },
    '7': {
      class_type: 'KSampler',
      inputs: {
        seed,
        steps,
        cfg,
        sampler_name: 'euler',
        scheduler: 'normal',
        denoise: 1,
        model: ['3', 0],
        positive: ['4', 0],
        negative: ['5', 0],
        latent_image: ['6', 0],
      },
    },
    '8': { class_type: 'VAEDecode', inputs: { samples: ['7', 0], vae: ['3', 2] } },
    '9': { class_type: 'SaveImage', inputs: { filename_prefix: 'continuum/realistic', images: ['8', 0] } },
  };
}

export async function generateRealistic(params: GenerateRealisticParams): Promise<GenerateRealisticResult> {
  if (!params.prompt || params.prompt.trim() === '') {
    throw new Error('prompt is required');
  }
  const seed = params.seed ?? Math.floor(Math.random() * 1000000000);
  const host = await resolveComfyUIHost();
  const workflow = buildWorkflow(params, seed);
  const promptRes = await fetch(`${host}/prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: workflow }),
  });
  if (!promptRes.ok) {
    const text = await promptRes.text().catch(() => '');
    throw new Error(`ComfyUI POST /prompt failed: ${promptRes.status} ${text}`);
  }
  const promptData = (await promptRes.json()) as { prompt_id: string };
  const promptId = promptData.prompt_id;
  if (!promptId) throw new Error('ComfyUI did not return prompt_id');
  const history = await pollHistory(host, promptId);
  const imagePath = await resolveImagePath(host, promptId, history);
  return { imagePath, seed, prompt: params.prompt };
}

async function pollHistory(host: string, promptId: string, maxAttempts = 60, intervalMs = 1000): Promise<Record<string, unknown>> {
  for (let i = 0; i < maxAttempts; i++) {
    const res = await fetch(`${host}/history/${promptId}`);
    if (res.ok) {
      const data = (await res.json()) as Record<string, unknown>;
      const entry = data[promptId] as Record<string, unknown> | undefined;
      if (entry) {
        const outputs = entry['outputs'] as Record<string, unknown> | undefined;
        if (outputs && Object.keys(outputs).length > 0) return data;
        const status = entry['status'] as Record<string, unknown> | undefined;
        if (status && status['completed'] === true) return data;
      }
      if (Object.keys(data).length > 0 && !data[promptId]) return data;
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`ComfyUI poll timeout for prompt_id ${promptId}`);
}

async function resolveImagePath(host: string, promptId: string, history: Record<string, unknown>): Promise<string> {
  try {
    const entry = history[promptId] as Record<string, unknown> | undefined;
    if (entry) {
      const outputs = entry['outputs'] as Record<string, Record<string, unknown>> | undefined;
      if (outputs) {
        for (const nodeId of Object.keys(outputs)) {
          const out = outputs[nodeId] as { images?: Array<{ filename: string; subfolder: string; type: string }> };
          if (out.images && out.images.length > 0) {
            const img = out.images[0];
            try {
              const viewUrl = `${host}/view?filename=${encodeURIComponent(img.filename)}&subfolder=${encodeURIComponent(img.subfolder)}&type=${encodeURIComponent(img.type)}`;
              const viewRes = await fetch(viewUrl);
              if (viewRes.ok) {
                const buf = await viewRes.arrayBuffer();
                const outDir = 'C:/OmniRoute/ComfyUI/output';
                const localPath = `${outDir}/${img.filename}`;
                try {
                  const fs = await import('fs/promises');
                  const path = await import('path');
                  await fs.mkdir(path.dirname(localPath), { recursive: true });
                  await fs.writeFile(localPath, Buffer.from(buf));
                  return localPath;
                } catch {
                  return `${outDir}/${img.filename}`;
                }
              }
            } catch {}
            return `C:/OmniRoute/ComfyUI/output/${img.filename}`;
          }
        }
      }
    }
  } catch {}
  return `C:/OmniRoute/ComfyUI/output/${promptId}.png`;
}
