import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { PROJECT_ROOT } from './shell.ts';
import { generateBrief } from './briefs.ts';

const DEFAULT_BASE_URL = 'http://127.0.0.1:5055';

function config() {
  const baseUrl = (process.env.OPEN_NOTEBOOK_API_URL || DEFAULT_BASE_URL).replace(/\/$/, '');
  const token = process.env.OPEN_NOTEBOOK_TOKEN || process.env.OPEN_NOTEBOOK_PASSWORD || '';
  return { baseUrl, token };
}

async function request(path: string, init: RequestInit = {}) {
  const { baseUrl, token } = config();
  const headers = new Headers(init.headers);
  headers.set('Content-Type', headers.get('Content-Type') || 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const res = await fetch(`${baseUrl}${path}`, { ...init, headers });
  const text = await res.text();
  let body: unknown = text;
  try { body = text ? JSON.parse(text) : null; } catch { /* keep raw text */ }
  return { ok: res.ok, status: res.status, body };
}

export async function openNotebookStatus() {
  const health = await request('/health');
  const auth = await request('/api/auth/status');
  const notebooks = await request('/api/notebooks');
  return {
    ok: health.ok,
    baseUrl: config().baseUrl,
    health: health.body,
    auth: auth.body,
    authenticated: notebooks.ok,
    notebooksStatus: notebooks.status,
    note: notebooks.ok ? 'Open Notebook API is reachable and authenticated.' : 'Set OPEN_NOTEBOOK_TOKEN or OPEN_NOTEBOOK_PASSWORD in the Flue server environment for authenticated API calls.',
  };
}

export async function listOpenNotebooks() {
  const res = await request('/api/notebooks');
  return { ok: res.ok, status: res.status, notebooks: res.body };
}

export async function ensureNotebook(name = 'Future Caribbean Dispatch', description = 'Evidence artifacts and generated briefs from Abeng.') {
  const list = await request('/api/notebooks');
  if (!list.ok || !Array.isArray(list.body)) return { status: list.status, ok: false, error: 'Could not list notebooks', detail: list.body };
  const existing = list.body.find((n: any) => String(n?.name || '').toLowerCase() === name.toLowerCase());
  if (existing) return { ok: true, created: false, notebook: existing };
  const created = await request('/api/notebooks', {
    method: 'POST',
    body: JSON.stringify({ name, description }),
  });
  return { ok: created.ok, created: created.ok, status: created.status, notebook: created.body };
}

export async function pushCycleToOpenNotebook(input: { notebookName?: string; includeRawJson?: boolean } = {}) {
  const notebookName = input.notebookName || 'Future Caribbean Dispatch';
  const ensured = await ensureNotebook(notebookName);
  if (!ensured.ok) return { ...ensured, ok: false, step: 'ensure_notebook' };
  const notebook: any = ensured.notebook;
  const notebookId = notebook?.id || notebook?.notebook_id || notebook?.uuid;
  if (!notebookId) return { ok: false, step: 'notebook_id', error: 'Open Notebook response did not include a notebook id.', notebook };

  const deskRaw = await readFile(join(PROJECT_ROOT, 'outbox', 'dispatch_desk.json'), 'utf8');
  const desk = JSON.parse(deskRaw);
  const brief = await generateBrief({ audience: 'investor', channel: 'memo', maxClusters: 5 });
  const markdown = [
    `# Abeng — ${desk.cycle_id || 'current cycle'}`,
    '',
    brief.brief,
    '',
    '## Machine summary',
    '',
    `- Cycle: ${desk.cycle_id || 'unknown'}`,
    `- Clusters: ${desk.cluster_count ?? desk.clusters?.length ?? 'unknown'}`,
    `- Dispatches: ${desk.dispatch_count ?? 'unknown'}`,
    '',
    input.includeRawJson ? ['## Raw dispatch_desk.json', '', '```json', deskRaw.slice(0, 60_000), '```'].join('\n') : '',
  ].filter(Boolean).join('\n');

  const title = `Future Caribbean Dispatch ${desk.cycle_id || new Date().toISOString().slice(0, 10)}`;
  const source = await request('/api/sources/json', {
    method: 'POST',
    body: JSON.stringify({
      type: 'text',
      title,
      content: markdown,
      notebooks: [notebookId],
      embed: false,
      async_processing: false,
    }),
  });
  return { ok: source.ok, status: source.status, notebookId, title, source: source.body };
}
