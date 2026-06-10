import { type WorkflowRouteHandler } from '@flue/runtime';
import { applyFeedback } from '../tools/feedback-apply.ts';

export const route: WorkflowRouteHandler = async (_c, next) => next();

export async function run() {
  return applyFeedback();
}
