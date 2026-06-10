import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { PROJECT_ROOT, runCommand } from './shell.ts';

export async function applyFeedback() {
  const result = await runCommand('python3', ['packagers/feedback_loop.py', 'apply'], 60_000);
  return {
    ok: result.exitCode === 0,
    command: result.command,
    exitCode: result.exitCode,
    stdout: result.stdout.trim(),
    stderr: result.stderr.trim() || undefined,
    boosts: await readCurrentBoosts(),
  };
}

export async function readCurrentBoosts() {
  try {
    const raw = await readFile(join(PROJECT_ROOT, 'data', 'feedback', 'current_boosts.json'), 'utf8');
    return { ok: true, ...JSON.parse(raw) };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : String(error) };
  }
}
