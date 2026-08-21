import { CommandBase, type ICommandDaemon } from '../../../../daemons/command-daemon/shared/CommandBase';
import type { JTAGContext } from '../../../../system/core/types/JTAGTypes';
import type { ImageGenerateRealisticParams, ImageGenerateRealisticResult } from '../shared/ImageGenerateRealisticTypes';

export class ImageGenerateRealisticBrowserCommand extends CommandBase<ImageGenerateRealisticParams, ImageGenerateRealisticResult> {
  static readonly commandName = 'image/generate-realistic';

  constructor(context: JTAGContext, subpath: string, commander: ICommandDaemon) {
    super('image/generate-realistic', context, subpath, commander);
  }

  async execute(params: ImageGenerateRealisticParams): Promise<ImageGenerateRealisticResult> {
    return (await this.remoteExecute(params)) as unknown as ImageGenerateRealisticResult;
  }
}
