import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { PROJECT_ROOT } from './shell.ts';

type PersonaRoute = {
  persona?: string;
  channel?: string;
  action?: string;
  dispatch_id?: string;
  feedback_status?: string;
  rationale?: string;
};

type Cluster = {
  title?: string;
  country_cluster?: string;
  decision?: string;
  evidence?: string;
  evidence_grade?: string;
  confidence_score?: number;
  feedback_summary?: string;
  freshness?: string;
  risk_flags?: string[];
  personas?: PersonaRoute[];
};

async function loadDesk() {
  const raw = await readFile(join(PROJECT_ROOT, 'outbox', 'dispatch_desk.json'), 'utf8');
  return JSON.parse(raw) as { cycle_id?: string; clusters?: Cluster[]; boost_lines?: string[]; cluster_count?: number; dispatch_count?: number };
}

export async function generateBrief(input: { audience?: string; channel?: string; maxClusters?: number }) {
  const audience = String(input.audience || 'investor').toLowerCase();
  const channel = String(input.channel || 'memo').toLowerCase();
  const maxClusters = Number.isFinite(input.maxClusters) ? Math.max(1, Math.min(8, Number(input.maxClusters))) : 3;
  const desk = await loadDesk();
  const clusters = (desk.clusters || []).slice(0, maxClusters);

  const lines: string[] = [];
  if (channel.includes('whatsapp') || channel.includes('telegram')) {
    lines.push(`Abeng — ${desk.cycle_id || 'current cycle'}`);
    lines.push('');
    for (const [i, cluster] of clusters.entries()) {
      lines.push(`${i + 1}. ${cluster.title || 'Untitled signal'}`);
      lines.push(`Evidence: ${cluster.evidence || 'n/a'} (${cluster.evidence_grade || 'grade n/a'})`);
      const route = chooseRoute(cluster, audience);
      if (route?.action) lines.push(`Action: ${route.action}`);
      if (cluster.risk_flags?.length) lines.push(`Risk: ${cluster.risk_flags[0]}`);
      lines.push('');
    }
    lines.push('Screening intelligence only. Not investment advice.');
  } else {
    lines.push(`# Abeng — ${desk.cycle_id || 'current cycle'}`);
    lines.push('');
    lines.push(`Audience: ${audience}`);
    lines.push(`Format: ${channel}`);
    lines.push('');
    lines.push('## Executive view');
    lines.push('');
    const lead = clusters[0];
    if (lead) {
      lines.push(`${lead.title || 'Untitled signal'}`);
      lines.push('');
      lines.push(`Decision supported: ${lead.decision || 'Which signal deserves action.'}`);
      lines.push(`Evidence: ${lead.evidence || 'n/a'} (${lead.evidence_grade || 'grade n/a'}).`);
      lines.push(`Confidence: ${lead.confidence_score ?? 'n/a'}/100. Freshness: ${lead.freshness || 'unknown'}.`);
      if (lead.feedback_summary) lines.push(`Feedback: ${lead.feedback_summary}`);
      if (lead.risk_flags?.length) lines.push(`Risk note: ${lead.risk_flags.join('; ')}`);
      lines.push('');
    }
    lines.push('## Routes');
    lines.push('');
    for (const cluster of clusters) {
      const route = chooseRoute(cluster, audience);
      lines.push(`### ${cluster.country_cluster || 'Region'} — ${cluster.title || 'Untitled signal'}`);
      lines.push(`- Evidence: ${cluster.evidence || 'n/a'} (${cluster.evidence_grade || 'grade n/a'})`);
      lines.push(`- Persona: ${route?.persona || audience}`);
      lines.push(`- Channel: ${route?.channel || channel}`);
      lines.push(`- Recommended action: ${route?.action || cluster.decision || 'Review and validate locally.'}`);
      lines.push(`- Dispatch ID: ${route?.dispatch_id || 'n/a'}`);
      lines.push('');
    }
    lines.push('Screening intelligence only. Not investment advice. Validate locally before acting.');
    lines.push('');
    lines.push('Sources: `outbox/dispatch_desk.json`, `outbox/opportunity_dispatches.json`');
  }

  return {
    ok: true,
    cycleId: desk.cycle_id ?? null,
    audience,
    channel,
    clusterCount: clusters.length,
    brief: lines.join('\n').trim(),
  };
}

function chooseRoute(cluster: Cluster, audience: string): PersonaRoute | undefined {
  const routes = cluster.personas || [];
  return routes.find((r) => String(r.persona || '').toLowerCase().includes(audience)) || routes[0];
}
