import { type WorkflowRouteHandler } from '@flue/runtime';
import { sendApproved } from '../tools/delivery.ts';

export const route: WorkflowRouteHandler = async (_c, next) => next();

export async function run({ payload }: { payload?: { approvalId?: string; dryRun?: boolean } }) {
  return sendApproved({ approvalId: payload?.approvalId, dryRun: payload?.dryRun });
}
