import { CommandBase, type ICommandDaemon } from '../../../../daemons/command-daemon/shared/CommandBase';
import type { JTAGContext, JTAGPayload } from '../../../../system/core/types/JTAGTypes';
import type { TtsSpeakParams, TtsSpeakResult } from '../shared/TtsSpeakTypes';
import { createTtsSpeakResult } from '../shared/TtsSpeakTypes';

export class TtsSpeakBrowserCommand extends CommandBase<TtsSpeakParams, TtsSpeakResult> {
  constructor(context: JTAGContext, subpath: string, commander: ICommandDaemon) {
    super('tts/speak', context, subpath, commander);
  }

  async execute(params: JTAGPayload): Promise<TtsSpeakResult> {
    const p = params as TtsSpeakParams;
    return createTtsSpeakResult(p, {
      success: false,
      error: 'tts/speak not supported in browser - use server (Kokoro/Voicebox HTTP)',
    });
  }
}
