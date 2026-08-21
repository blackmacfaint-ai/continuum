import { CommandBase, type ICommandDaemon } from '../../../../daemons/command-daemon/shared/CommandBase';
import type { JTAGContext, JTAGPayload } from '../../../../system/core/types/JTAGTypes';
import type { FFmpegTiktokParams, FFmpegTiktokResult } from '../shared/FFmpegTiktokTypes';

export class FFmpegTiktokBrowserCommand extends CommandBase<FFmpegTiktokParams, FFmpegTiktokResult> {
  constructor(context: JTAGContext, subpath: string, commander: ICommandDaemon) {
    super('ffmpeg_tiktok', context, subpath, commander);
  }

  async execute(params: JTAGPayload): Promise<FFmpegTiktokResult> {
    return this.remoteExecute<FFmpegTiktokParams, FFmpegTiktokResult>(params as FFmpegTiktokParams);
  }
}
