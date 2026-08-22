import { CommandBase, type ICommandDaemon } from '../../../../daemons/command-daemon/shared/CommandBase';
import type { JTAGContext, JTAGPayload } from '../../../../system/core/types/JTAGTypes';
import type { YoutubeUploadParams, YoutubeUploadResult } from '../shared/YoutubeUploadTypes';
import { createYoutubeUploadResult, youtubeUpload } from '../shared/YoutubeUploadTypes';

export class YoutubeUploadServerCommand extends CommandBase<YoutubeUploadParams, YoutubeUploadResult> {
  constructor(context: JTAGContext, subpath: string, commander: ICommandDaemon) {
    super('youtube/upload', context, subpath, commander);
  }

  async execute(params: JTAGPayload): Promise<YoutubeUploadResult> {
    const p = params as YoutubeUploadParams;
    try {
      const res = await youtubeUpload(p);
      if (!res.success && !res.skipped) return createYoutubeUploadResult(p, { success: false, error: res.error });
      return res;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return createYoutubeUploadResult(p, { success: false, error: msg });
    }
  }
}
