import { type WorkflowRouteHandler } from '@flue/runtime';
import { runPipeline } from '../tools/pipeline.ts';

export const route: WorkflowRouteHandler = async (_c, next) => next();

export async function run() {
  return runPipeline();
}
