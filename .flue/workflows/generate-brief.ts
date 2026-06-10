import { type WorkflowRouteHandler } from '@flue/runtime';
import { generateBrief } from '../tools/briefs.ts';

export const route: WorkflowRouteHandler = async (_c, next) => next();

export async function run({ payload }: { payload: { audience?: string; channel?: string; maxClusters?: number } }) {
  return generateBrief({
    audience: payload?.audience,
    channel: payload?.channel,
    maxClusters: payload?.maxClusters,
  });
}
