import { readFile, stat } from 'node:fs/promises';
import { join, normalize } from 'node:path';
import { PROJECT_ROOT } from './shell.ts';

const ALLOWED_PREFIXES = ['outbox/', 'data/feedback/', 'data/composite/', 'domains/', 'config/recipients.json'];

export async function listKeyArtifacts() {
  const paths = [
    'outbox/dispatch_desk.json',
    'outbox/dispatch_desk.md',
    'outbox/opportunity_dispatches.json',
    'outbox/telegram_brief.md',
    'outbox/investor_brief.md',
    'outbox/judge_brief.md',
    'outbox/delivery_manifest.json',
    'outbox/feedback_review.md',
    'outbox/reasoning.json',
    'outbox/climate_desk.json',
    'data/feedback/current_boosts.json',
    'data/feedback/available.json',
    'data/feedback/state.json',
  ];

  const rows = [];
  for (const path of paths) {
    try {
      const s = await stat(join(PROJECT_ROOT, path));
      rows.push({ path, exists: true, size: s.size, modifiedAt: s.mtime.toISOString() });
    } catch {
      rows.push({ path, exists: false });
    }
  }
  return rows;
}

export async function readArtifact(path: string, maxBytes = 40_000) {
  const safe = normalize(String(path || '')).replace(/^\.\/+/, '');
  if (safe.includes('..') || safe.startsWith('/') || !ALLOWED_PREFIXES.some((p) => safe.startsWith(p) || safe === p.replace(/\/$/, ''))) {
    return { ok: false, path: safe, error: 'Path is outside the allowed artifact prefixes.' };
  }

  try {
    const abs = join(PROJECT_ROOT, safe);
    const s = await stat(abs);
    const raw = await readFile(abs, 'utf8');
    const truncated = raw.length > maxBytes;
    return {
      ok: true,
      path: safe,
      size: s.size,
      modifiedAt: s.mtime.toISOString(),
      truncated,
      content: truncated ? raw.slice(0, maxBytes) : raw,
    };
  } catch (error) {
    return { ok: false, path: safe, error: error instanceof Error ? error.message : String(error) };
  }
}
