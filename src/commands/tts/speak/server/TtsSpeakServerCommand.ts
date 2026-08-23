import { CommandBase, type ICommandDaemon } from '../../../../daemons/command-daemon/shared/CommandBase';
import type { JTAGContext, JTAGPayload } from '../../../../system/core/types/JTAGTypes';
import type { TtsSpeakParams, TtsSpeakResult } from '../shared/TtsSpeakTypes';
import { createTtsSpeakResult, ttsSpeak } from '../shared/TtsSpeakTypes';

export class TtsSpeakServerCommand extends CommandBase<TtsSpeakParams, TtsSpeakResult> {
  constructor(context: JTAGContext, subpath: string, commander: ICommandDaemon) {
    super('tts/speak', context, subpath, commander);
  }

  async execute(params: JTAGPayload): Promise<TtsSpeakResult> {
    const p = params as TtsSpeakParams;
    try {
      const res = await ttsSpeak(p);
      return createTtsSpeakResult(p, res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return createTtsSpeakResult(p, { success: false, error: msg });
    }
  }
}
