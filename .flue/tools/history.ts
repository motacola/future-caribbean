import { copyFile, mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { PROJECT_ROOT } from './shell.ts';

const HISTORY_ROOT = join(PROJECT_ROOT, 'data', 'history', 'cycles');
const HISTORY_INDEX = join(PROJECT_ROOT, 'data', 'history', 'index.json');

const ARCHIVE_ARTIFACTS = [
  'outbox/dispatch_desk.json',
  'outbox/dispatch_desk.md',
  'outbox/opportunity_dispatches.json',
  'outbox/opportunity_dispatches.md',
  'outbox/delivery_manifest.json',
  'outbox/judge_brief.md',
  'outbox/investor_brief.md',
  'outbox/telegram_brief.md',
  'outbox/feedback_review.md',
  'outbox/reasoning.json',
];

async function readJson(path: string) {
  return JSON.parse(await readFile(path, 'utf8'));
}

export async function archiveCurrentCycle(input: { cycleId?: string; overwrite?: boolean } = {}) {
  const deskPath = join(PROJECT_ROOT, 'outbox', 'dispatch_desk.json');
  const desk = await readJson(deskPath);
  const cycleId = String(input.cycleId || desk.cycle_id || new Date().toISOString().slice(0, 10).replaceAll('-', ''));
  const archiveDir = join(HISTORY_ROOT, cycleId);
  // Paths in the index are served publicly by /api/history. Record them
  // relative to the repo root: an absolute path leaks the layout of whatever
  // machine ran the cycle and means nothing to a caller anywhere else.
  const archiveDirRel = ['data', 'history', 'cycles', cycleId].join('/');

  try {
    const existing = await stat(archiveDir);
    if (existing.isDirectory() && !input.overwrite) {
      return { ok: false, cycleId, archiveDir: archiveDirRel, error: 'Archive already exists. Pass overwrite=true to replace files.' };
    }
  } catch {
    // no archive yet
  }

  await mkdir(archiveDir, { recursive: true });
  const copied = [];
  for (const rel of ARCHIVE_ARTIFACTS) {
    try {
      const src = join(PROJECT_ROOT, rel);
      const name = rel.replaceAll('/', '__');
      const dst = join(archiveDir, name);
      await copyFile(src, dst);
      const s = await stat(dst);
      copied.push({ path: rel, archivePath: `${archiveDirRel}/${name}`, size: s.size });
    } catch (error) {
      copied.push({ path: rel, skipped: true, error: error instanceof Error ? error.message : String(error) });
    }
  }

  const entry = {
    cycleId,
    archivedAt: new Date().toISOString(),
    archiveDir: archiveDirRel,
    clusterCount: desk.cluster_count ?? desk.clusters?.length ?? null,
    dispatchCount: desk.dispatch_count ?? null,
    leadTitle: desk.clusters?.[0]?.title ?? null,
    leadCountry: desk.clusters?.[0]?.country_cluster ?? null,
    artifacts: copied,
  };

  await mkdir(join(PROJECT_ROOT, 'data', 'history'), { recursive: true });
  let index: any[] = [];
  try {
    const raw = await readFile(HISTORY_INDEX, 'utf8');
    const parsed = JSON.parse(raw);
    index = Array.isArray(parsed.cycles) ? parsed.cycles : [];
  } catch {
    index = [];
  }
  index = [entry, ...index.filter((e) => e.cycleId !== cycleId)].slice(0, 100);
  await writeFile(HISTORY_INDEX, JSON.stringify({ updatedAt: new Date().toISOString(), cycles: index }, null, 2) + '\n', 'utf8');
  return { ok: true, ...entry };
}

export async function listCycleHistory(limit = 20) {
  try {
    const raw = await readFile(HISTORY_INDEX, 'utf8');
    const parsed = JSON.parse(raw);
    return { ok: true, updatedAt: parsed.updatedAt ?? null, cycles: (parsed.cycles || []).slice(0, Math.max(1, Math.min(100, limit))) };
  } catch (error) {
    return { ok: true, cycles: [], note: error instanceof Error ? error.message : String(error) };
  }
}
