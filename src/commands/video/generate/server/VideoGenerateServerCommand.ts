import { CommandBase, type ICommandDaemon } from '../../../../daemons/command-daemon/shared/CommandBase';
import type { JTAGContext, JTAGPayload } from '../../../../system/core/types/JTAGTypes';
import type { VideoGenerateParams, VideoGenerateResult } from '../shared/VideoGenerateTypes';
import { createVideoGenerateResult, generateVideo } from '../shared/VideoGenerateTypes';

export class VideoGenerateServerCommand extends CommandBase<VideoGenerateParams, VideoGenerateResult> {
  constructor(context: JTAGContext, subpath: string, commander: ICommandDaemon) {
    super('video/generate', context, subpath, commander);
  }

  async execute(params: JTAGPayload): Promise<VideoGenerateResult> {
    const p = params as VideoGenerateParams;
    try {
      const res = await generateVideo(p);
      return createVideoGenerateResult(p, res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return createVideoGenerateResult(p, { success: false, error: msg });
    }
  }
}
