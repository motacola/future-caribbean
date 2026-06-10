import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { PROJECT_ROOT, runCommand } from './shell.ts';

export const VALID_FEEDBACK_STATUSES = new Set([
  'forwarded',
  'replied',
  'opened',
  'ignored',
  'decision_changed',
  'delivered',
]);

export async function recordFeedback(input: {
  dispatchId: string;
  status: string;
  note?: string;
  source?: string;
}) {
  const dispatchId = String(input.dispatchId || '').trim();
  const status = String(input.status || '').trim();
  const note = String(input.note || '').trim();
  const source = String(input.source || 'flue').trim();

  if (!/^DSP-[A-Za-z0-9-]+$/.test(dispatchId)) {
    return { ok: false, error: 'dispatchId must look like DSP-20260603-001', dispatchId, status };
  }
  if (!VALID_FEEDBACK_STATUSES.has(status)) {
    return { ok: false, error: `Invalid status: ${status}`, validStatuses: [...VALID_FEEDBACK_STATUSES] };
  }

  const result = await runCommand(
    'python3',
    ['packagers/feedback_intake.py', '--dispatch-id', dispatchId, '--status', status, '--note', note, '--source', source],
    60_000,
  );
  return {
    ok: result.exitCode === 0,
    dispatchId,
    status,
    command: result.command,
    exitCode: result.exitCode,
    stdout: result.stdout.trim(),
    stderr: result.stderr.trim() || undefined,
    available: await listAvailableFeedback(),
  };
}

export async function listAvailableFeedback() {
  try {
    const raw = await readFile(join(PROJECT_ROOT, 'data', 'feedback', 'available.json'), 'utf8');
    const items = JSON.parse(raw);
    return { ok: true, count: Array.isArray(items) ? items.length : 0, items: Array.isArray(items) ? items.slice(-20) : items };
  } catch (error) {
    return { ok: true, count: 0, items: [], note: error instanceof Error ? error.message : String(error) };
  }
}
