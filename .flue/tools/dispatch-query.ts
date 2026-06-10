import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { PROJECT_ROOT, runCommand } from './shell.ts';

export type DispatchAnswer = {
  ok: boolean;
  question: string;
  answer: string;
  command: string;
  exitCode: number | null;
  durationMs: number;
  stderr?: string;
};

export async function askDispatch(question: string): Promise<DispatchAnswer> {
  const cleanQuestion = String(question || '').trim() || 'explain lead';
  const result = await runCommand('python3', ['agent/query.py', 'ask', cleanQuestion], 60_000);
  return {
    ok: result.exitCode === 0,
    question: cleanQuestion,
    answer: result.stdout.trim(),
    command: result.command,
    exitCode: result.exitCode,
    durationMs: result.durationMs,
    stderr: result.stderr.trim() || undefined,
  };
}

export async function explainLead(): Promise<DispatchAnswer> {
  const result = await runCommand('python3', ['agent/query.py', 'explain-lead'], 60_000);
  return {
    ok: result.exitCode === 0,
    question: 'explain-lead',
    answer: result.stdout.trim(),
    command: result.command,
    exitCode: result.exitCode,
    durationMs: result.durationMs,
    stderr: result.stderr.trim() || undefined,
  };
}

export async function readDispatchDeskJson(): Promise<Record<string, unknown>> {
  const raw = await readFile(join(PROJECT_ROOT, 'outbox', 'dispatch_desk.json'), 'utf8');
  return JSON.parse(raw) as Record<string, unknown>;
}

export function summarizeDesk(desk: Record<string, unknown>) {
  const clusters = Array.isArray(desk.clusters) ? desk.clusters : [];
  const lead = clusters[0] as Record<string, unknown> | undefined;
  return {
    cycleId: desk.cycle_id ?? null,
    clusterCount: desk.cluster_count ?? clusters.length,
    dispatchCount: desk.dispatch_count ?? null,
    leadTitle: lead?.title ?? null,
    leadCountry: lead?.country_cluster ?? null,
    leadConfidence: lead?.confidence_score ?? null,
    evidenceGrade: lead?.evidence_grade ?? null,
  };
}
