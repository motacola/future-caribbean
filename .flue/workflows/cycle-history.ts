import { type WorkflowRouteHandler } from '@flue/runtime';
import { archiveCurrentCycle, listCycleHistory } from '../tools/history.ts';

export const route: WorkflowRouteHandler = async (_c, next) => next();

export async function run({ payload }: { payload?: { action?: string; cycleId?: string; overwrite?: boolean; limit?: number } }) {
  const action = payload?.action ?? 'archive';
  if (action === 'archive') return archiveCurrentCycle({ cycleId: payload?.cycleId, overwrite: payload?.overwrite });
  if (action === 'list') return listCycleHistory(payload?.limit);
  return { ok: false, error: `Unknown action: ${action}`, validActions: ['archive', 'list'] };
}
