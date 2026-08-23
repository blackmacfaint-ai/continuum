import { CommandBase, type ICommandDaemon } from '../../../../daemons/command-daemon/shared/CommandBase';
import type { JTAGContext, JTAGPayload } from '../../../../system/core/types/JTAGTypes';
import type { ArtifactsStoreParams, ArtifactsStoreResult } from '../shared/ArtifactsStoreTypes';
import { createArtifactsStoreResult, storeArtifact } from '../shared/ArtifactsStoreTypes';

export class ArtifactsStoreServerCommand extends CommandBase<ArtifactsStoreParams, ArtifactsStoreResult> {
  constructor(context: JTAGContext, subpath: string, commander: ICommandDaemon) {
    super('artifacts/store', context, subpath, commander);
  }

  async execute(params: JTAGPayload): Promise<ArtifactsStoreResult> {
    const p = params as ArtifactsStoreParams;
    try {
      const res = await storeArtifact(p);
      return createArtifactsStoreResult(p, res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return createArtifactsStoreResult(p, { success: false, error: msg });
    }
  }
}
