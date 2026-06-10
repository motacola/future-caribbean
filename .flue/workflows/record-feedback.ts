import { type WorkflowRouteHandler } from '@flue/runtime';
import { recordFeedback } from '../tools/feedback.ts';

export const route: WorkflowRouteHandler = async (_c, next) => next();

export async function run({ payload }: { payload: { dispatchId?: string; status?: string; note?: string; source?: string } }) {
  return recordFeedback({
    dispatchId: payload?.dispatchId ?? '',
    status: payload?.status ?? '',
    note: payload?.note ?? '',
    source: payload?.source ?? 'flue-workflow',
  });
}
