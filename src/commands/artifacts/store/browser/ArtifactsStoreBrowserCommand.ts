import { CommandBase, type ICommandDaemon } from '../../../../daemons/command-daemon/shared/CommandBase';
import type { JTAGContext, JTAGPayload } from '../../../../system/core/types/JTAGTypes';
import type { ArtifactsStoreParams, ArtifactsStoreResult } from '../shared/ArtifactsStoreTypes';
import { createArtifactsStoreResult } from '../shared/ArtifactsStoreTypes';

export class ArtifactsStoreBrowserCommand extends CommandBase<ArtifactsStoreParams, ArtifactsStoreResult> {
  constructor(context: JTAGContext, subpath: string, commander: ICommandDaemon) {
    super('artifacts/store', context, subpath, commander);
  }

  async execute(params: JTAGPayload): Promise<ArtifactsStoreResult> {
    const p = params as ArtifactsStoreParams;
    return createArtifactsStoreResult(p, {
      success: false,
      error: 'artifacts/store not supported in browser - use server',
    });
  }
}
