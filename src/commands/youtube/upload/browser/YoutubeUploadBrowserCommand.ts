import { CommandBase, type ICommandDaemon } from '../../../../daemons/command-daemon/shared/CommandBase';
import type { JTAGContext, JTAGPayload } from '../../../../system/core/types/JTAGTypes';
import type { YoutubeUploadParams, YoutubeUploadResult } from '../shared/YoutubeUploadTypes';
import { createYoutubeUploadResult } from '../shared/YoutubeUploadTypes';

export class YoutubeUploadBrowserCommand extends CommandBase<YoutubeUploadParams, YoutubeUploadResult> {
  constructor(context: JTAGContext, subpath: string, commander: ICommandDaemon) {
    super('youtube/upload', context, subpath, commander);
  }

  async execute(params: JTAGPayload): Promise<YoutubeUploadResult> {
    const p = params as YoutubeUploadParams;
    return createYoutubeUploadResult(p, {
      success: false,
      skipped: true,
      error: 'youtube/upload not supported in browser - use server',
      reason: 'browser stub',
    });
  }
}
