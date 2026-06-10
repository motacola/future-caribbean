import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { PROJECT_ROOT, runCommand } from './shell.ts';

export async function runPipeline() {
  const result = await runCommand('bash', ['run_pipeline.sh'], 180_000);
  const desk = await tryReadDeskSummary();
  return {
    ok: result.exitCode === 0,
    command: result.command,
    exitCode: result.exitCode,
    durationMs: result.durationMs,
    stdoutTail: tail(result.stdout, 80),
    stderrTail: tail(result.stderr, 80),
    desk,
  };
}

export async function tryReadDeskSummary() {
  try {
    const raw = await readFile(join(PROJECT_ROOT, 'outbox', 'dispatch_desk.json'), 'utf8');
    const desk = JSON.parse(raw) as Record<string, unknown>;
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
  } catch (error) {
    return { error: error instanceof Error ? error.message : String(error) };
  }
}

function tail(text: string, maxLines: number): string {
  const lines = text.trim().split('\n');
  return lines.slice(-maxLines).join('\n');
}
