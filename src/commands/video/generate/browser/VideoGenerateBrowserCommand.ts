import { CommandBase, type ICommandDaemon } from '../../../../daemons/command-daemon/shared/CommandBase';
import type { JTAGContext, JTAGPayload } from '../../../../system/core/types/JTAGTypes';
import type { VideoGenerateParams, VideoGenerateResult } from '../shared/VideoGenerateTypes';
import { createVideoGenerateResult } from '../shared/VideoGenerateTypes';

export class VideoGenerateBrowserCommand extends CommandBase<VideoGenerateParams, VideoGenerateResult> {
  constructor(context: JTAGContext, subpath: string, commander: ICommandDaemon) {
    super('video/generate', context, subpath, commander);
  }

  async execute(params: JTAGPayload): Promise<VideoGenerateResult> {
    const p = params as VideoGenerateParams;
    return createVideoGenerateResult(p, {
      success: false,
      error: 'video/generate not supported in browser - use server (ComfyUI + ffmpeg)',
    });
  }
}
