import type { CommandParams, JTAGPayload, CommandInput } from '../../../../system/core/types/JTAGTypes';
import * as fs from 'fs';
import * as path from 'path';
import { execFile } from 'child_process';

export type ArtifactType = 'video' | 'image' | 'audio' | 'document';

export interface ArtifactsStoreParams extends CommandParams {
  artifact: string;
  type: ArtifactType;
  tags?: string[];
  registry?: string;
}

export interface ArtifactsStoreResult extends JTAGPayload {
  success: boolean;
  artifactId?: string;
  path?: string;
  error?: string;
}

export function createArtifactsStoreResult(params: ArtifactsStoreParams, outcome: Partial<ArtifactsStoreResult>): ArtifactsStoreResult {
  return {
    success: outcome.success ?? false,
    artifactId: outcome.artifactId,
    path: outcome.path,
    error: outcome.error,
    context: params.context,
    sessionId: params.sessionId,
  };
}

function findHelper(): string | null {
  const candidates = [
    path.resolve(process.cwd(), 'scripts', 'artifacts_store.py'),
    path.resolve(__dirname, '../../../../../scripts/artifacts_store.py'),
    'C:/OmniRoute/repos/continuum/scripts/artifacts_store.py',
  ];
  for (const p of candidates) {
    try {
      if (fs.existsSync(p) && fs.statSync(p).isFile()) return p;
    } catch {}
  }
  return null;
}

export async function storeArtifact(params: ArtifactsStoreParams): Promise<ArtifactsStoreResult> {
  if (!params.artifact || !params.type) {
    return createArtifactsStoreResult(params, { success: false, error: 'artifact and type are required' });
  }
  const helper = findHelper();
  if (!helper) {
    return createArtifactsStoreResult(params, { success: false, error: 'scripts/artifacts_store.py not found' });
  }
  const artifactPath = path.resolve(params.artifact);
  if (!fs.existsSync(artifactPath)) {
    return createArtifactsStoreResult(params, { success: false, error: `artifact not found: ${artifactPath}` });
  }
  const args = [helper, '--artifact', artifactPath, '--type', params.type];
  if (params.tags && params.tags.length > 0) args.push('--tags', ...params.tags);
  if (params.registry) args.push('--registry', path.resolve(params.registry));
  try {
    const stdout = await runPython(helper, args);
    const data = JSON.parse(stdout) as ArtifactsStoreResult;
    return createArtifactsStoreResult(params, data);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return createArtifactsStoreResult(params, { success: false, error: `artifacts_store.py failed: ${msg}` });
  }
}

function runPython(helper: string, args: string[]): Promise<string> {
  return new Promise((resolvePromise, reject) => {
    execFile('python', args, { cwd: path.resolve(helper, '../..'), timeout: 60000, maxBuffer: 8 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) {
        const detail = stderr ? `\n${stderr.toString().slice(0, 800)}` : '';
        reject(new Error(`${error.message}${detail}`));
        return;
      }
      resolvePromise(stdout.toString());
    });
  });
}

export const ArtifactsStore = {
  async execute(params: CommandInput<ArtifactsStoreParams>): Promise<ArtifactsStoreResult> {
    const { Commands } = await import('../../../../system/core/shared/Commands');
    return Commands.execute<ArtifactsStoreParams, ArtifactsStoreResult>('artifacts/store', params as Partial<ArtifactsStoreParams>);
  },
  commandName: 'artifacts/store' as const,
} as const;
