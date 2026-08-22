import type { CommandParams, JTAGPayload, CommandInput } from '../../../../system/core/types/JTAGTypes';
import * as fs from 'fs';
import * as path from 'path';

export interface YoutubeUploadParams extends CommandParams {
  video?: string;
  videoPath?: string;
  title?: string;
  description?: string;
  privacy?: 'public' | 'private' | 'unlisted';
  category?: string;
  tags?: string[];
  clientSecretsPath?: string;
}

export interface YoutubeUploadResult extends JTAGPayload {
  success: boolean;
  skipped?: boolean;
  videoId?: string;
  url?: string;
  error?: string;
  reason?: string;
}

export function createYoutubeUploadResult(params: YoutubeUploadParams, outcome: Partial<YoutubeUploadResult>): YoutubeUploadResult {
  return {
    success: outcome.success ?? false,
    skipped: outcome.skipped,
    videoId: outcome.videoId,
    url: outcome.url,
    error: outcome.error,
    reason: outcome.reason,
    context: params.context,
    sessionId: params.sessionId,
  };
}

export function resolveYoutubeUploadParams(params: YoutubeUploadParams): YoutubeUploadParams {
  return {
    ...params,
    video: params.video ?? params.videoPath,
    title: params.title?.slice(0, 100) ?? 'Money Printer Realistic - Faceless TikTok',
    description: params.description?.slice(0, 5000) ?? params.title ?? '',
    privacy: params.privacy ?? 'public',
    category: params.category ?? 'faceless',
  };
}

export function findClientSecrets(customPath?: string): string | null {
  const candidates = [
    customPath,
    path.resolve('config/client_secrets.json'),
    path.resolve('config/youtube_client_secrets.json'),
    path.resolve('C:/OmniRoute/repos/continuum/config/client_secrets.json'),
    process.env.GOOGLE_APPLICATION_CREDENTIALS,
    process.env.YOUTUBE_CLIENT_SECRETS,
  ].filter(Boolean) as string[];
  for (const p of candidates) {
    try {
      if (fs.existsSync(p) && fs.statSync(p).isFile()) {
        const content = fs.readFileSync(p, 'utf-8');
        JSON.parse(content);
        return p;
      }
    } catch {}
  }
  return null;
}

export async function youtubeUpload(params: YoutubeUploadParams): Promise<YoutubeUploadResult> {
  const resolved = resolveYoutubeUploadParams(params);
  const videoPath = resolved.video ? path.resolve(resolved.video) : null;

  if (!videoPath || !fs.existsSync(videoPath)) {
    return createYoutubeUploadResult(params, {
      success: false,
      skipped: true,
      error: `video not found: ${videoPath ?? 'undefined'}`,
      reason: 'missing video file - skip per money-printer-realistic onError:skip',
    });
  }

  const stat = fs.statSync(videoPath);
  if (stat.size < 1000) {
    return createYoutubeUploadResult(params, {
      success: false,
      skipped: true,
      error: `video too small: ${stat.size} bytes`,
      reason: 'invalid artifact',
    });
  }

  const secretsPath = findClientSecrets(resolved.clientSecretsPath);
  if (!secretsPath) {
    return createYoutubeUploadResult(params, {
      success: false,
      skipped: true,
      error: 'client_secrets.json not found',
      reason: 'missing Google Cloud OAuth credentials - create Kanban card GOOGLE-CLOUD-YOUTUBE and place config/client_secrets.json (see helper scripts/youtube_upload.py)',
    });
  }

  return createYoutubeUploadResult(params, {
    success: false,
    skipped: true,
    error: `credentials found at ${secretsPath} but upload not yet implemented - run helper: python scripts/youtube_upload.py --file "${videoPath}" --title "${resolved.title?.replace(/"/g, "'")}" --privacy ${resolved.privacy}`,
    reason: 'stub - helper required for resumable upload',
  });
}

export const YoutubeUpload = {
  async execute(params: CommandInput<YoutubeUploadParams>): Promise<YoutubeUploadResult> {
    const { Commands } = await import('../../../../system/core/shared/Commands');
    return Commands.execute<YoutubeUploadParams, YoutubeUploadResult>('youtube/upload', params as Partial<YoutubeUploadParams>);
  },
  commandName: 'youtube/upload' as const,
} as const;
