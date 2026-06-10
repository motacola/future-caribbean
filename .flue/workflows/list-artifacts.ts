import { type WorkflowRouteHandler } from '@flue/runtime';
import { listKeyArtifacts, readArtifact } from '../tools/artifacts.ts';

export const route: WorkflowRouteHandler = async (_c, next) => next();

export async function run({ payload }: { payload?: { path?: string; maxBytes?: number } }) {
  if (payload?.path) return readArtifact(payload.path, payload.maxBytes);
  return { ok: true, artifacts: await listKeyArtifacts() };
}
