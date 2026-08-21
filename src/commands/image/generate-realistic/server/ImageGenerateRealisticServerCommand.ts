import { CommandBase, type ICommandDaemon } from '../../../../daemons/command-daemon/shared/CommandBase';
import type { JTAGContext } from '../../../../system/core/types/JTAGTypes';
import type { ImageGenerateRealisticParams, ImageGenerateRealisticResult } from '../shared/ImageGenerateRealisticTypes';
import { createImageGenerateRealisticResultFromParams } from '../shared/ImageGenerateRealisticTypes';
import { generateRealistic } from '../shared/comfyui';

export class ImageGenerateRealisticServerCommand extends CommandBase<ImageGenerateRealisticParams, ImageGenerateRealisticResult> {
  static readonly commandName = 'image/generate-realistic';

  constructor(context: JTAGContext, subpath: string, commander: ICommandDaemon) {
    super('image/generate-realistic', context, subpath, commander);
  }

  async execute(params: ImageGenerateRealisticParams): Promise<ImageGenerateRealisticResult> {
    if (!params.prompt || params.prompt.trim() === '') {
      return createImageGenerateRealisticResultFromParams(params, {
        success: false,
        imagePath: '',
        seed: params.seed ?? 0,
        prompt: params.prompt ?? '',
        error: 'prompt is required',
      });
    }

    try {
      const result = await generateRealistic({
        prompt: params.prompt,
        negativePrompt: params.negativePrompt,
        width: params.width,
        height: params.height,
        steps: params.steps,
        cfg: params.cfg,
        seed: params.seed,
        checkpoint: params.checkpoint,
      });

      return createImageGenerateRealisticResultFromParams(params, {
        success: true,
        imagePath: result.imagePath,
        seed: result.seed,
        prompt: result.prompt,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return createImageGenerateRealisticResultFromParams(params, {
        success: false,
        imagePath: '',
        seed: params.seed ?? 0,
        prompt: params.prompt,
        error: msg,
      });
    }
  }
}
