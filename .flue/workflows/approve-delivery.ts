import { type WorkflowRouteHandler } from '@flue/runtime';
import { approveDelivery, listApprovals } from '../tools/delivery.ts';

export const route: WorkflowRouteHandler = async (_c, next) => next();

export async function run({ payload }: { payload?: { approvalId?: string; approvedBy?: string; note?: string; reject?: boolean; list?: boolean; limit?: number } }) {
  if (payload?.list || !payload?.approvalId) return listApprovals(payload?.limit);
  return approveDelivery({ approvalId: payload.approvalId, approvedBy: payload.approvedBy, note: payload.note, reject: payload.reject });
}
