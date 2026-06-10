import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { PROJECT_ROOT, runCommand } from './shell.ts';

const APPROVAL_DIR = join(PROJECT_ROOT, 'data', 'approvals');
const APPROVAL_FILE = join(APPROVAL_DIR, 'delivery_approvals.json');

const CHANNEL_FILES: Record<string, string> = {
  telegram: 'outbox/telegram_digest.md',
  telegram_brief: 'outbox/telegram_brief.md',
  investor: 'outbox/investor_brief.md',
  judge: 'outbox/judge_brief.md',
};

type ApprovalRecord = {
  approvalId: string;
  cycleId: string;
  channel: string;
  file: string;
  status: 'pending' | 'approved' | 'sent' | 'dry-run-sent' | 'rejected';
  createdAt: string;
  updatedAt: string;
  approvedBy?: string;
  note?: string;
  sendResult?: unknown;
};

async function loadApprovals(): Promise<ApprovalRecord[]> {
  try {
    const raw = await readFile(APPROVAL_FILE, 'utf8');
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed.approvals) ? parsed.approvals : [];
  } catch {
    return [];
  }
}

async function saveApprovals(approvals: ApprovalRecord[]) {
  await mkdir(APPROVAL_DIR, { recursive: true });
  await writeFile(APPROVAL_FILE, JSON.stringify({ updatedAt: new Date().toISOString(), approvals }, null, 2) + '\n', 'utf8');
}

async function currentCycleId() {
  try {
    const desk = JSON.parse(await readFile(join(PROJECT_ROOT, 'outbox', 'dispatch_desk.json'), 'utf8'));
    return String(desk.cycle_id || new Date().toISOString().slice(0, 10).replaceAll('-', ''));
  } catch {
    return new Date().toISOString().slice(0, 10).replaceAll('-', '');
  }
}

export async function prepareDelivery(input: { channel?: string; file?: string } = {}) {
  const channel = String(input.channel || 'telegram').toLowerCase();
  const relFile = input.file || CHANNEL_FILES[channel] || CHANNEL_FILES.telegram;
  const absFile = join(PROJECT_ROOT, relFile);
  const content = await readFile(absFile, 'utf8');
  const cycleId = await currentCycleId();
  const approvalId = `APP-${cycleId}-${channel}-${Date.now().toString(36)}`;
  const now = new Date().toISOString();
  const record: ApprovalRecord = {
    approvalId,
    cycleId,
    channel,
    file: relFile,
    status: 'pending',
    createdAt: now,
    updatedAt: now,
  };
  const approvals = await loadApprovals();
  approvals.unshift(record);
  await saveApprovals(approvals.slice(0, 100));
  return {
    ok: true,
    approval: record,
    preview: content.slice(0, 3000),
    truncated: content.length > 3000,
    instruction: 'Call approve-delivery with this approvalId before send-approved. send-approved defaults to dryRun=true.',
  };
}

export async function approveDelivery(input: { approvalId: string; approvedBy?: string; note?: string; reject?: boolean }) {
  const approvals = await loadApprovals();
  const approval = approvals.find((a) => a.approvalId === input.approvalId);
  if (!approval) return { ok: false, error: 'approvalId not found', approvalId: input.approvalId };
  if (!['pending', 'approved'].includes(approval.status)) return { ok: false, error: `Cannot change approval in status ${approval.status}`, approval };
  approval.status = input.reject ? 'rejected' : 'approved';
  approval.approvedBy = input.approvedBy || 'operator';
  approval.note = input.note || approval.note;
  approval.updatedAt = new Date().toISOString();
  await saveApprovals(approvals);
  return { ok: true, approval };
}

export async function listApprovals(limit = 20) {
  const approvals = await loadApprovals();
  return { ok: true, approvals: approvals.slice(0, Math.max(1, Math.min(100, limit))) };
}

export async function sendApproved(input: { approvalId?: string; dryRun?: boolean } = {}) {
  const dryRun = input.dryRun !== false;
  const approvals = await loadApprovals();
  const approval = approvals.find((a) => a.approvalId === input.approvalId);
  if (!approval) return { ok: false, error: 'approvalId not found', approvalId: input.approvalId };
  if (approval.status !== 'approved') return { ok: false, error: `Approval status must be approved, got ${approval.status}`, approval };
  if (approval.channel !== 'telegram') return { ok: false, error: `Channel ${approval.channel} is not sendable yet.`, approval };

  const args = ['distributors/telegram_sender.py', '--file', approval.file];
  if (dryRun) args.push('--dry-run');
  const result = await runCommand('python3', args, 90_000);
  const nextStatus = dryRun ? 'dry-run-sent' : 'sent';
  if (result.exitCode === 0) {
    approval.status = nextStatus;
  }
  approval.updatedAt = new Date().toISOString();
  approval.sendResult = {
    dryRun,
    exitCode: result.exitCode,
    stdout: result.stdout.slice(-6000),
    stderr: result.stderr.slice(-3000),
  };
  await saveApprovals(approvals);
  return { ok: result.exitCode === 0, approval, command: result.command, exitCode: result.exitCode };
}
