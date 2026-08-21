import { CommandBase, type ICommandDaemon } from '../../../../daemons/command-daemon/shared/CommandBase';
import type { JTAGContext, JTAGPayload } from '../../../../system/core/types/JTAGTypes';
import type { FFmpegTiktokParams, FFmpegTiktokResult } from '../shared/FFmpegTiktokTypes';
import { createFFmpegTiktokResult, ffmpegTiktok } from '../shared/FFmpegTiktokTypes';

export class FFmpegTiktokServerCommand extends CommandBase<FFmpegTiktokParams, FFmpegTiktokResult> {
  constructor(context: JTAGContext, subpath: string, commander: ICommandDaemon) {
    super('ffmpeg_tiktok', context, subpath, commander);
  }

  async execute(params: JTAGPayload): Promise<FFmpegTiktokResult> {
    const p = params as FFmpegTiktokParams;
    try {
      const res = await ffmpegTiktok(p);
      if (!res.success) return createFFmpegTiktokResult(p, { success: false, error: res.error });
      return res;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return createFFmpegTiktokResult(p, { success: false, error: msg });
    }
  }
}
