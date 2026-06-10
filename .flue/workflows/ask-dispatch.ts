import { type WorkflowRouteHandler } from '@flue/runtime';
import { askDispatch } from '../tools/dispatch-query.ts';

export const route: WorkflowRouteHandler = async (_c, next) => next();

export async function run({ payload }: { payload: { question?: string } }) {
  const question = payload?.question ?? 'explain lead';
  return askDispatch(question);
}
