import { type WorkflowRouteHandler } from '@flue/runtime';
import { listOpenNotebooks, openNotebookStatus, pushCycleToOpenNotebook } from '../tools/open-notebook.ts';

export const route: WorkflowRouteHandler = async (_c, next) => next();

export async function run({ payload }: { payload?: { action?: string; notebookName?: string; includeRawJson?: boolean } }) {
  const action = payload?.action ?? 'status';
  if (action === 'status') return openNotebookStatus();
  if (action === 'list') return listOpenNotebooks();
  if (action === 'push-cycle') return pushCycleToOpenNotebook({ notebookName: payload?.notebookName, includeRawJson: payload?.includeRawJson });
  return { ok: false, error: `Unknown action: ${action}`, validActions: ['status', 'list', 'push-cycle'] };
}
