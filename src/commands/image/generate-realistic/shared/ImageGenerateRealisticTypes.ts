import type { CommandParams, CommandResult, CommandInput, JTAGContext } from '../../../../system/core/types/JTAGTypes';
import { createPayload, transformPayload } from '../../../../system/core/types/JTAGTypes';
import { SYSTEM_SCOPES } from '../../../../system/core/types/SystemScopes';
import { Commands } from '../../../../system/core/shared/Commands';
import type { UUID } from '../../../../system/core/types/CrossPlatformUUID';

export interface ImageGenerateRealisticParams extends CommandParams {
  prompt: string;
  negativePrompt?: string;
  width?: number;
  height?: number;
  steps?: number;
  cfg?: number;
  seed?: number;
  checkpoint?: string;
}

export const createImageGenerateRealisticParams = (
  context: JTAGContext,
  sessionId: UUID,
  data: Omit<ImageGenerateRealisticParams, 'context' | 'sessionId' | 'userId'>
): ImageGenerateRealisticParams => createPayload(context, sessionId, {
  userId: SYSTEM_SCOPES.SYSTEM,
  ...data
});

export interface ImageGenerateRealisticResult extends CommandResult {
  success: boolean;
  imagePath: string;
  seed: number;
  prompt: string;
  error?: string;
}

export const createImageGenerateRealisticResult = (
  context: JTAGContext,
  sessionId: UUID,
  data: {
    success: boolean;
    imagePath: string;
    seed: number;
    prompt: string;
    error?: string;
  }
): ImageGenerateRealisticResult => createPayload(context, sessionId, {
  userId: SYSTEM_SCOPES.SYSTEM,
  ...data
});

export const createImageGenerateRealisticResultFromParams = (
  params: ImageGenerateRealisticParams,
  differences: Omit<Partial<ImageGenerateRealisticResult>, 'context' | 'sessionId' | 'userId'>
): ImageGenerateRealisticResult => transformPayload(params, {
  success: false,
  imagePath: '',
  seed: 0,
  prompt: params.prompt,
  ...differences
});

export const ImageGenerateRealistic = {
  execute(params: CommandInput<ImageGenerateRealisticParams>): Promise<ImageGenerateRealisticResult> {
    return Commands.execute<ImageGenerateRealisticParams, ImageGenerateRealisticResult>('image/generate-realistic', params as Partial<ImageGenerateRealisticParams>);
  },
  commandName: 'image/generate-realistic' as const,
} as const;
