// Port of dashboard/generate.py data loading + transformation.
// Runs at Astro build time (Node.js); reads JSON files from the repo root.

import { readFileSync, existsSync, readdirSync, statSync } from 'fs';
import { resolve, join } from 'path';
import { humanize, humanizeRulesJson } from './humanize.ts';

const ROOT = resolve(process.cwd());

function readJson(path: string): any {
  const p = join(ROOT, path);
  try {
    if (!existsSync(p)) return null;
    return JSON.parse(readFileSync(p, 'utf-8'));
  } catch { return null; }
}

function readText(path: string): string {
  const p = join(ROOT, path);
  try { return readFileSync(p, 'utf-8'); } catch { return ''; }
}

// fallow-ignore-next-line complexity
function age(ts: string | undefined | null): string {
  if (!ts) return '—';
  try {
    const m = Math.floor((Date.now() - new Date(ts).getTime()) / 60000);
    if (m < 2) return 'just now';
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
  } catch { return '——'; }
}

function esc(value: any): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Label cleaners (port of generate.py functions) ──────────

function cleanTitle(raw: string): string {
  const country = raw.includes(':') ? raw.split(':')[0].trim() : 'Caribbean';
  return `All signals point to ${country}.`;
}

// fallow-ignore-next-line complexity
function cleanGrade(raw: string): string {
  const r = raw.toLowerCase();
  if (r.includes('multi-source') || raw.startsWith('A')) return 'Solid — several sources agree';
  if (r.includes('cross-source') || raw.startsWith('B')) return 'Promising — more than one source';
  if (raw.startsWith('C')) return 'Early — one source so far';
  return 'Exploratory';
}

function cleanEvidence(raw: string): string {
  return raw
    .replace(/WB\s+/g, 'World Bank ')
    .replace(/detected:\s*/g, 'data shows: ')
    .replace(/FDI surge/g, 'FDI movement');
}

function cleanSignalTitle(raw: string): string {
  const country = raw.includes(':') ? raw.split(':')[0].trim() : 'Caribbean';
  const pct = raw.match(/([+\-]?\d+\.?\d*)%/);
  if (pct) return `${country} — money on the move (${pct[1]}%)`;
  return `${country} — early signal`;
}

// ── Country data ────────────────────────────────────────────

const COUNTRY_COORDS: Record<string, [number, number]> = {
  'Bahamas': [24.70, -77.80], 'Belize': [17.25, -88.76],
  'Jamaica': [18.11, -77.30], 'Haiti': [18.97, -72.69],
  'Dominican Republic': [18.79, -70.16], 'Puerto Rico': [18.22, -66.42],
  'Antigua & Barbuda': [17.08, -61.80], 'St Lucia': [13.91, -60.98],
  'Barbados': [13.16, -59.55], 'Grenada': [12.11, -61.68],
  'Trinidad & Tobago': [10.46, -61.25], 'Guyana': [4.86, -58.93],
  'Suriname': [3.92, -56.03], 'St Kitts & Nevis': [17.35, -62.73],
  'St Vincent & the Grenadines': [13.15, -61.23], 'Dominica': [15.41, -61.37],
  'Cayman Islands': [19.31, -81.25], 'Turks & Caicos': [21.69, -71.79],
  'Montserrat': [16.74, -62.18], 'Anguilla': [18.22, -63.05],
  'British Virgin Islands': [18.42, -64.61], 'US Virgin Islands': [18.34, -64.93],
  'Cuba': [21.52, -77.78],
};

const OECS_MARKETS = new Set([
  'Antigua & Barbuda', 'St Lucia', 'Grenada', 'St Kitts & Nevis',
  'St Vincent & the Grenadines', 'Dominica', 'Montserrat', 'Anguilla',
]);

const COUNTRY_FX: Record<string, any> = {
  'Belize': { currency:'BZD', pair:'USD/BZD', rate_label:'2.00 peg', indicator:'USD peg', signal:'watch reserves, tourism receipts, imports, and remittance demand' },
  'Haiti': { currency:'HTG', pair:'USD/HTG', rate_label:'floating', indicator:'FX stress', signal:'watch inflation, remittances, fuel imports, and liquidity' },
  'Dominican Republic': { currency:'DOP', pair:'USD/DOP', rate_label:'floating', indicator:'FX float', signal:'watch tourism, remittances, and import pressure' },
  'Puerto Rico': { currency:'USD', pair:'USD', rate_label:'US dollar', indicator:'USD base', signal:'watch US rates, tourism, logistics, and municipal finance' },
  'Suriname': { currency:'SRD', pair:'USD/SRD', rate_label:'floating', indicator:'FX stress', signal:'watch inflation, reserves, gold/oil flows, and import costs' },
  'Turks & Caicos': { currency:'USD', pair:'USD', rate_label:'US dollar', indicator:'USD base', signal:'watch tourism receipts, real estate, and US rate sensitivity' },
  'British Virgin Islands': { currency:'USD', pair:'USD', rate_label:'US dollar', indicator:'USD base', signal:'watch financial services, tourism, and company registry flows' },
  'US Virgin Islands': { currency:'USD', pair:'USD', rate_label:'US dollar', indicator:'USD base', signal:'watch tourism, logistics, and US fiscal flows' },
  'Cuba': { currency:'CUP', pair:'USD/CUP', rate_label:'managed / multiple rates', indicator:'FX controls', signal:'watch tourism, remittances, sanctions exposure, and import constraints' },
};

const KIND_COLORS: Record<string, string> = {
  'enhanced_investment':'#2676A8', 'investment_signal':'#2676A8',
  'climate':'#0D766E', 'weather':'#0D766E',
  'procurement':'#B57A22', 'development_pipeline':'#B57A22',
};

function kindColor(kind: string): string {
  const entry = Object.entries(KIND_COLORS).find(([k]) => kind.includes(k));
  return entry ? entry[1] : '#7F8C83';
}

function canonicalCountry(raw: string): string {
  if (!raw) return '';
  const ALIAS: Record<string, string> = {
    'T&T': 'Trinidad & Tobago', 'TT': 'Trinidad & Tobago',
    'T and T': 'Trinidad & Tobago', 'SVG': 'St Vincent & the Grenadines',
    'St. Vincent': 'St Vincent & the Grenadines', 'DR': 'Dominican Republic',
    'BVI': 'British Virgin Islands', 'USVI': 'US Virgin Islands',
    'SKN': 'St Kitts & Nevis', 'ANT': 'Antigua & Barbuda',
  };
  return ALIAS[raw.trim()] ?? raw.trim();
}

// ── Validation pack HTML builders ──────────────────────────

// fallow-ignore-next-line complexity
function packFreshnessStrip(pack: any): string {
  const freshness = pack.evidence_freshness || 'unknown';
  const cycles = parseInt(pack.cycles_since_refresh || '0', 10) || 0;
  const readiness = pack.action_readiness || 'n/a';
  const raw = pack.raw_confidence_score ?? pack.confidence_score ?? '—';
  const calibrated = pack.confidence_score ?? '—';
  const validated = age(pack.last_validated_at);
  const labelMap: Record<string, string> = { refreshing:'Refreshing', aging:'Aging', stale:'Stale — downgrade risk' };
  const label = labelMap[freshness] ?? freshness.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
  const cycleNote = cycles === 0 ? 'new evidence this cycle' : `${cycles} cycle${cycles === 1 ? '' : 's'} since evidence changed`;
  return `<div class="vpack-freshness">
    <span class="freshness-pill ${esc(freshness)}">${esc(label)}</span>
    <span class="freshness-meta">Action readiness: <strong>${esc(readiness)}</strong></span>
    <span class="freshness-meta">Confidence: <strong>${esc(calibrated)}</strong> calibrated <em>(raw ${esc(raw)})</em></span>
    <span class="freshness-meta">Validated ${esc(validated)} · ${esc(cycleNote)}</span>
  </div>`;
}

// fallow-ignore-next-line complexity
function packHypothesisLi(h: any): string {
  const status = h.status || '';
  const badge = status
    ? `<span class="hyp-status ${esc(status)}">${esc(status.replace(/_/g, ' '))}</span>` : '';
  const basis = h.basis ? `<em>${esc(humanize(h.basis))}</em>` : '';
  return `<li><strong>${esc(h.sector || '')}</strong>${badge}${basis}</li>`;
}

// fallow-ignore-next-line complexity
function packOperatorLi(o: any): string {
  const url = o.source_url || '';
  const name = esc(o.name || '');
  const role = esc(humanize(o.role || ''));
  if (url) return `<li><a href="${esc(url)}" target="_blank" rel="noopener"><strong>${name}</strong></a><em>${role}</em></li>`;
  return `<li><strong>${name}</strong><em>${role}</em></li>`;
}

// fallow-ignore-next-line complexity
function packProcurementLi(p: any, titleLen = 90): string {
  const url = p.url || '';
  const title = esc((p.title || '').slice(0, titleLen));
  const tag = p.match ? `<span class="vpack-tag">${esc(p.match)}</span>` : '';
  const closeTag = p.closing_date ? `<span class="vpack-tag closing">closes ${esc(p.closing_date)}</span>` : '';
  if (url) return `<li><a href="${esc(url)}" target="_blank" rel="noopener">${title}</a>${tag}${closeTag}</li>`;
  return `<li>${title}${tag}${closeTag}</li>`;
}

// fallow-ignore-next-line complexity
function buildValidationPackHtml(pack: any, country: string): string {
  if (!pack) return '';
  const verdict = pack.advance_or_reject_recommendation || 'hold';
  const verdictLabel = { advance:'Advance', hold:'Hold', reject:'Reject' }[verdict as string] ?? 'Hold';

  const hypLis = ((pack.sector_hypotheses || []) as any[]).slice(0, 5).map(packHypothesisLi).join('')
    || '<li>No sector hypotheses generated this cycle.</li>';
  const opLis = ((pack.credible_local_operators || []) as any[]).slice(0, 4).map(packOperatorLi).join('')
    || '<li>No registry-backed operators for this country yet.</li>';
  // fallow-ignore-next-line complexity
  const projLis = ((pack.supporting_projects || []) as any[]).slice(0, 4).map((p: any) => {
    const url = p.url || '';
    const title = esc((p.title || '').slice(0, 90));
    if (url) return `<li><a href="${esc(url)}" target="_blank" rel="noopener">${title}</a><em>${esc(p.source || '')}</em></li>`;
    return `<li>${title}</li>`;
  }).join('') || '<li>No matched projects this cycle.</li>';
  const procLis = ((pack.procurement_matches || []) as any[]).slice(0, 4).map((p: any) => packProcurementLi(p)).join('')
    || '<li>No live procurement notices matched.</li>';
  const qLis = ((pack.unresolved_questions || []) as any[]).slice(0, 4)
    .map((q: any) => `<li>${esc(humanize(q))}</li>`).join('');

  return `<div class="vpack">
    <div class="vpack-head">
      <div>
        <span>Validation pack · auto-assembled this cycle</span>
        <h3>What the system already checked for ${esc(pack.country || country)}</h3>
      </div>
      <span class="vpack-verdict ${esc(verdict)}">${esc(verdictLabel)}</span>
    </div>
    ${packFreshnessStrip(pack)}
    <div class="vpack-reason">${esc(humanize(pack.recommendation_reason || ''))}</div>
    <div class="vpack-grid">
      <div class="vpack-col"><h4>Sector hypotheses</h4><ul>${hypLis}</ul></div>
      <div class="vpack-col"><h4>Registry operators</h4><ul>${opLis}</ul></div>
      <div class="vpack-col"><h4>Supporting projects &amp; data</h4><ul>${projLis}</ul></div>
      <div class="vpack-col"><h4>Procurement pipeline</h4><ul>${procLis}</ul></div>
    </div>
    <div class="vpack-questions"><h4>Still unresolved — what to validate this week</h4><ul>${qLis}</ul></div>
  </div>`;
}

// fallow-ignore-next-line complexity
function buildSignalRowHtml(c: any, allPacks: Record<string, any>, cycleId: string): { html: string; verdict: string } {
  const ct = cleanSignalTitle(c.title || '');
  const cc = c.country_cluster || '';
  const riskHtml = c.risk_flags?.length
    ? `<span class="risk-tag">⚠️ ${esc((c.risk_flags[0] || '').slice(0, 50))}</span>` : '';

  const sid = c.signal_id || '';
  let verdict = 'hold';
  if (sid && allPacks[sid]) verdict = allPacks[sid].advance_or_reject_recommendation || 'hold';

  const kind = c.signal_kind || '';
  const deskName = kind.includes('invest') ? 'Investment Desk'
    : (kind.includes('climate') || kind.includes('weather')) ? 'Climate Desk'
    : (kind.includes('procure') || kind.includes('pipeline')) ? 'Procurement Desk'
    : 'Regional Desk';
  const deskColor = { 'Investment Desk':'#2676A8', 'Climate Desk':'#0D766E', 'Procurement Desk':'#B57A22' }[deskName] || '#7F8C83';
  const dek = esc(humanize(c.decision || '').slice(0, 110));

  let validationHtml = '';
  if (sid && allPacks[sid]) {
    const pack = allPacks[sid];
    const vl = { advance:'Advance', hold:'Hold', reject:'Reject' }[verdict as string] ?? 'Hold';
    const fresh = pack.evidence_freshness || 'unknown';
    const freshLabel = { refreshing:'Refreshing', aging:'Aging', stale:'Stale' }[fresh as string] ?? fresh;
    const cycles = parseInt(pack.cycles_since_refresh || '0', 10) || 0;
    const hypLis = ((pack.sector_hypotheses || []) as any[]).slice(0, 3).map(packHypothesisLi).join('')
      || '<li>No sector hypotheses this cycle.</li>';
    // fallow-ignore-next-line complexity
    const projLis = ((pack.supporting_projects || []) as any[]).slice(0, 2).map((p: any) => {
      const url = p.url || '';
      const title = esc((p.title || '').slice(0, 80));
      return url ? `<li><a href="${esc(url)}" target="_blank" rel="noopener">${title}</a><em>${esc(p.source || '')}</em></li>` : `<li>${title}</li>`;
    }).join('') || '<li>No matched projects.</li>';
    const procLis = ((pack.procurement_matches || []) as any[]).slice(0, 2).map((p: any) => packProcurementLi(p, 80)).join('')
      || '<li>No procurement matches.</li>';
    const unresolvedLis = ((pack.unresolved_questions || []) as any[]).slice(0, 2)
      .map((q: any) => `<li>${esc(q)}</li>`).join('') || '<li>All questions resolved.</li>';

    validationHtml = `<div class="sig-validation">
      <div class="sig-validation-inner">
        <div class="sig-validation-head">
          <span>Validation pack · auto-assembled this cycle</span>
          <h4>Evidence for ${esc(pack.country || cc)}</h4>
          <span class="sig-validation-verdict ${esc(verdict)}">${esc(vl)}</span>
        </div>
        <div class="sig-freshness">
          <span class="freshness-pill ${esc(fresh)}">${esc(freshLabel)}</span>
          <span class="freshness-meta">${esc(pack.action_readiness || 'n/a')} · ${esc(String(cycles))} cycles stale · conf ${esc(pack.confidence_score ?? '—')}</span>
        </div>
        <div class="sig-validation-grid">
          <div class="sig-validation-col"><h5>Sector hypotheses</h5><ul>${hypLis}</ul></div>
          <div class="sig-validation-col"><h5>Projects &amp; data</h5><ul>${projLis}</ul></div>
          <div class="sig-validation-col"><h5>Procurement pipeline</h5><ul>${procLis}</ul></div>
          <div class="sig-validation-col"><h5>Still unresolved</h5><ul>${unresolvedLis}</ul></div>
        </div>
      </div>
    </div>`;
  }

  return {
    verdict,
    html: `<div class="sig-row" data-verdict="${esc(verdict)}" data-signal-id="${esc(sid)}">
      <div class="sig-main"><div>
        <span class="art-kicker" style="color:${deskColor}">${esc(deskName)}</span>
        <strong class="art-head">${esc(ct)}</strong>
        <div class="sig-loc">${esc(cc)}</div>
        <p class="art-dek">${dek}</p>
        <span class="art-by">By the Desk · Cycle ${esc(cycleId)}</span>
      </div></div>
      ${riskHtml}
      <span class="sig-expand" aria-label="Expand validation" title="View validation pack">▼</span>
      ${validationHtml}
    </div>`,
  };
}

// ── Main data loader ────────────────────────────────────────

// fallow-ignore-next-line complexity
export function loadDashboardData() {
  const desk = readJson('outbox/dispatch_desk.json') || {};
  const clusters: any[] = desk.clusters || [];
  const lead = clusters[0] || {};
  const dispatchData = readJson('outbox/opportunity_dispatches.json') || {};
  const dispatches: any[] = dispatchData.dispatches || [];
  const marketSources = readJson('config/market_sources.json') || {};
  const markets: any[] = marketSources.markets || [];
  const feedback = readJson('data/feedback/state.json') || {};
  const trackRecord = readJson('outbox/track_record.json');

  // ── Market helpers ─────────────────────────────────────────
  function marketProfileFor(country: string): any {
    const direct = markets.find((m: any) => m.country === country);
    if (direct) return direct;
    if (OECS_MARKETS.has(country)) return markets.find((m: any) => m.id === 'eastern_caribbean') || {};
    return {};
  }
  function fxProfileFor(country: string): any {
    const m = marketProfileFor(country);
    return m.fx || COUNTRY_FX[country] || {};
  }
  function snapshotFor(country: string): any {
    const m = marketProfileFor(country);
    return m.market_snapshot || {};
  }

  // ── Map markers ────────────────────────────────────────────
  // For Astro we use a slim map_data stub reading dispatch data directly.
  // (map_data.py reads composite signals; here we approximate from clusters.)
  const clusterByCountry: Record<string, any> = {};
  for (const c of clusters) {
    const cc = canonicalCountry(c.country_cluster || '');
    if (!clusterByCountry[cc]) clusterByCountry[cc] = c;
  }

  // fallow-ignore-next-line complexity
  const mapMarkers = Object.entries(COUNTRY_COORDS).map(([country, [lat, lng]]) => {
    const c = clusterByCountry[country] || {};
    return {
      country, lat, lng,
      confidence: c.confidence_score || 0,
      kind: c.signal_kind ? (c.signal_kind.includes('invest') ? 'investment'
        : c.signal_kind.includes('climate') || c.signal_kind.includes('weather') ? 'climate'
        : c.signal_kind.includes('procure') || c.signal_kind.includes('pipeline') ? 'procurement'
        : 'none') : 'none',
      summary: humanize(c.top_signal_summary || c.decision || ''),
      ranking_rationale: humanize(c.ranking_rationale || ''),
      fx: fxProfileFor(country),
      market: {
        code: (marketProfileFor(country).exchange || {}).code || '',
        name: (marketProfileFor(country).exchange || {}).name || '',
        status: (marketProfileFor(country).exchange || {}).feed_status || '',
        snapshot: snapshotFor(country),
      },
    };
  });

  // ── Map dispatches ─────────────────────────────────────────
  const mapDispatches: Record<string, any[]> = Object.fromEntries(
    Object.keys(COUNTRY_COORDS).map(c => [c, []])
  );
  for (const d of dispatches) {
    const country = canonicalCountry(d.country_cluster || '');
    if (mapDispatches[country]) {
      mapDispatches[country].push({
        dispatch_id: d.dispatch_id,
        title: humanize(d.title || ''),
        recommended_action: humanize(d.recommended_action || ''),
        confidence_score: d.confidence_score || 0,
        signal_kind: d.signal_kind || '',
        persona_label: d.persona_label || '',
        ranking_rationale: humanize(d.ranking_rationale || ''),
      });
    }
  }

  // ── Ticker ─────────────────────────────────────────────────
  const seenTicker: Record<string, any> = {};
  for (const d of dispatches) {
    const sid = d.signal_id || d.dispatch_id || '';
    if (!seenTicker[sid] || (d.confidence_score || 0) > (seenTicker[sid].confidence_score || 0)) {
      seenTicker[sid] = d;
    }
  }
  const tickerItems = Object.values(seenTicker)
    .sort((a, b) => (b.confidence_score || 0) - (a.confidence_score || 0))
    .slice(0, 12);

  // fallow-ignore-next-line complexity
  let tickerHtml = tickerItems.map((t: any) => {
    const color = kindColor(t.signal_kind || '');
    const country = canonicalCountry(t.country_cluster || '');
    return `<a class="lw-item" href="#leaflet-map" data-country="${esc(country)}">` +
      `<i style="background:${color}"></i>` +
      `<span class="lw-kicker">${esc(t.country_cluster || 'Region')}</span>` +
      `<span>${esc(humanize(t.title || ''))}</span></a>`;
  }).join('');

  // ── Front pointers ─────────────────────────────────────────
  let frontPointersHtml = tickerItems.slice(1, 4).map((t: any) => {
    const country = canonicalCountry(t.country_cluster || '');
    return `<a class="fp-item" href="#leaflet-map" data-country="${esc(country)}">` +
      `<span class="fp-kicker">${esc(t.country_cluster || 'Region')}</span>` +
      `<span class="fp-title">${esc(humanize(t.title || ''))}</span></a>`;
  }).join('');

  // ── Lead signal ────────────────────────────────────────────
  const lCountry = lead.country_cluster || 'Guyana';
  const lTitle = cleanTitle(lead.title || '');
  const lEvidence = humanize(cleanEvidence(lead.evidence || ''));
  const lRanking = humanize(lead.ranking_rationale || '')
    || 'Ranking uses confidence, source coverage, evidence count, magnitude, and feedback.';
  const lDecision = humanize(lead.decision || 'Which opportunity deserves your attention first');
  const lGrade = cleanGrade(lead.evidence_grade || '');
  const lRisks: string[] = lead.risk_flags || [];
  const leadPctMatch = (lead.title || '').match(/([+\-]?\d+\.?\d*)%/);
  const leadPctStr = leadPctMatch ? leadPctMatch[1] + '%' : '';

  // ── Lead dispatch ──────────────────────────────────────────
  const leadDispatches = dispatches.filter(
    d => d.country_cluster === lCountry && d.signal_kind === lead.signal_kind
  );
  const leadDispatch = leadDispatches.find(d => d.persona_key === 'diaspora_investor')
    || leadDispatches[0] || {};

  const leadAction = humanize(leadDispatch.recommended_action
    || 'Validate sector fit, local partners, and timing before advancing this opportunity.');
  const leadWindow = leadDispatch.action_window || '14 days';
  const leadOwner = leadDispatch.persona_label || 'Diaspora Investor';
  const leadDispatchId = leadDispatch.dispatch_id || lead.cluster_id || 'lead-dispatch';
  const leadDelivery = (leadDispatch.delivery_status || 'queued').replace(/_/g, ' ')
    .replace(/\b\w/g, (c: string) => c.toUpperCase());
  const leadFeedback = (leadDispatch.feedback_status || 'awaiting').replace(/_/g, ' ')
    .replace(/\b\w/g, (c: string) => c.toUpperCase());
  const leadRationale = humanize(leadDispatch.routing_rationale
    || 'This route matches a high-confidence signal to the person most likely to advance it.');

  // fallow-ignore-next-line complexity
  const leadRoutesHtml = leadDispatches.slice(0, 3).map((r: any) =>
    `<div class="route-lane">
      <div>
        <strong>${esc(r.persona_label || 'Decision-maker')}</strong>
        <span>${esc(r.channel || 'Brief')} · ${esc(r.action_window || '14 days')}</span>
      </div>
      <p>${esc(humanize(r.recommended_action || ''))}</p>
      <span class="route-state">${esc((r.feedback_status || 'awaiting').replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()))}</span>
    </div>`
  ).join('');

  // ── Validation packs ───────────────────────────────────────
  const vpIndex = readJson('outbox/validation_packs/index.json') || {};
  const allPacks: Record<string, any> = {};
  for (const entry of (vpIndex.packs || []) as any[]) {
    const sid = entry.signal_id;
    if (!sid) continue;
    const safe = sid.replace(/[^A-Za-z0-9._-]/g, '-');
    const pack = readJson(`outbox/validation_packs/${safe}.json`);
    if (pack) allPacks[sid] = pack;
  }

  const vpSid = leadDispatch.signal_id || '';
  const vpFile = vpSid ? vpSid.replace(/[^A-Za-z0-9._-]/g, '-') : '';
  const vpack = allPacks[vpSid] || (vpFile ? readJson(`outbox/validation_packs/${vpFile}.json`) : null);
  const validationPackHtml = buildValidationPackHtml(vpack, lCountry);

  // ── Persona cards ──────────────────────────────────────────
  const pcards: [string, string, string][] = [];
  const seen = new Set<string>();
  for (const c of clusters) {
    for (const p of (c.personas || []) as any[]) {
      const name = p.persona || '';
      if (!name || seen.has(name)) continue;
      seen.add(name);
      pcards.push([name, p.channel || '', (humanize(p.action || '') || '').slice(0, 100)]);
    }
    if (pcards.length >= 5) break;
  }

  // ── Sources ────────────────────────────────────────────────
  const SRC_DEFS = [
    ['World Bank Indicators', 'world_bank', 'REST API · 5 indicators × 13 countries'],
    ['IDB Open Data', 'idb', 'CKAN API · Regional project datasets'],
    ['NOAA Weather Alerts', 'noaa', 'NWS API · Active hazard alerts'],
    ['NDBC Marine Buoys', 'ndbc', 'Marine conditions · 6 buoys'],
    ['CARICOM Statistics', 'tier2', 'WordPress REST · 126 datasets'],
    ['CDB Procurement Feed', 'tier2', 'RSS · Project & procurement notices'],
  ] as [string, string, string][];

  let nSources = 0;
  // fallow-ignore-next-line complexity
  const srcRows = SRC_DEFS.map(([label, key, desc]) => {
    const d = readJson(`data/${key}/latest.json`);
    const ok = d !== null;
    if (ok) nSources++;
    const a = age(d?.fetched_at);
    let ageMin: number | null = null;
    if (d?.fetched_at) {
      try { ageMin = Math.floor((Date.now() - new Date(d.fetched_at).getTime()) / 60000); } catch {}
    }
    const stale = ageMin !== null && ageMin > 360;
    const status = ok && stale ? 'Stale — fallback cached' : ok ? 'Live' : 'Offline — needs connector check';
    const dot = ok && stale ? '◐' : ok ? '●' : '○';
    const cls = ok && stale ? 'src-stale' : ok ? 'src-ok' : 'src-off';
    return { label, desc, a, status, dot, cls };
  });

  // ── Secondary signals ──────────────────────────────────────
  const cycleId = desk.cycle_id || '—';
  let advanceCount = 0, holdCount = 0, rejectCount = 0;
  const secSignals = clusters.slice(1, 5).map(c => {
    const { html, verdict } = buildSignalRowHtml(c, allPacks, cycleId);
    if (verdict === 'advance') advanceCount++;
    else if (verdict === 'hold') holdCount++;
    else rejectCount++;
    return html;
  }).join('') || '<p class="muted">No additional signals</p>';

  // ── Feedback ───────────────────────────────────────────────
  const fbHist: any[] = feedback.history || [];
  const fbBoosts: Record<string, any> = feedback.boosts || {};
  const fbActions: Record<string, number> = {};
  for (const e of fbHist) {
    const s = e.feedback_status || 'unknown';
    fbActions[s] = (fbActions[s] || 0) + 1;
  }
  const ICONS: Record<string, string> = { forwarded:'📤', replied:'💬', opened:'👁', decision_changed:'🔀' };
  const fbActionPills = Object.entries(fbActions)
    .filter(([a]) => a !== 'ignored')
    .sort(([, a], [, b]) => b - a)
    .map(([act, cnt]) => `<span class="fb-pill">${ICONS[act] || '•'} ${act.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}: ${cnt}</span>`)
    .join('') || '<span class="muted">No delivery responses yet</span>';

  // ── Track record ───────────────────────────────────────────
  let receiptsHtml = '';
  let boostsHtml = '';
  let receiptsProvenanceHtml = '';
  if (trackRecord) {
    const cycles: any[] = trackRecord.cycles || [];
    const currentBoosts: Record<string, any> = trackRecord.current_boosts || {};
    if (trackRecord.feedback_provenance !== 'observed') {
      receiptsProvenanceHtml = `<p class="receipts-note"><strong>Validation note:</strong> these seeded responses exercise the feedback and reprioritisation loop. Observed recipient outcomes replace them as audience activity accumulates.</p>`;
    }
    const PILL_ORDER = [
      ['forwarded','Forwarded'], ['replied','Replied'],
      ['decision_changed','Changed a decision'], ['opened','Opened'],
    ];
    // fallow-ignore-next-line complexity
    receiptsHtml = cycles.slice(0, 6).map((c: any) => {
      const rid = c.cycle_id || '';
      let cycleDate = rid;
      try {
        const dt = new Date(rid.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3'));
        cycleDate = dt.toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' });
      } catch {}
      const responses: any = c.responses || {};
      const dispatchCount = c.dispatch_count || 0;
      const countries: string[] = c.countries || [];
      const leadC = (c.lead || {}).country || 'Region';
      const leadT = (c.lead || {}).title || `${dispatchCount} briefings routed`;
      const pills = PILL_ORDER.map(([key, label]) => {
        const n = responses[key] || 0;
        return n ? `<span class="r-pill">${esc(label)} ${n}</span>` : '';
      }).join('') || '<span class="r-pill r-quiet">No responses yet</span>';
      return `<div class="receipt-row">
        <div class="receipt-when"><strong>${esc(cycleDate)}</strong><span>Cycle ${esc(rid)}</span></div>
        <div class="receipt-said">
          <span class="fp-kicker">${esc(leadC)}</span>
          <strong>${esc(leadT)}</strong>
          <p>${dispatchCount} briefings · ${countries.length} markets: ${esc(countries.slice(0, 4).join(', '))}</p>
        </div>
        <div class="receipt-resp">${pills}</div>
      </div>`;
    }).join('');

    const net: Record<string, number> = {};
    for (const countries of Object.values(currentBoosts)) {
      for (const [country, val] of Object.entries(countries as Record<string, number>)) {
        net[country] = (net[country] || 0) + (Number(val) || 0);
      }
    }
    boostsHtml = Object.entries(net)
      .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
      .slice(0, 5)
      .filter(([, val]) => val !== 0)
      .map(([country, val]) => {
        const dir = val > 0 ? 'up' : 'down';
        const arrow = val > 0 ? '▲' : '▼';
        const sign = val > 0 ? '+' : '';
        return `<span class="r-boost ${dir}">${esc(country)} ${arrow}${sign}${val}</span>`;
      }).join('');
  }

  // ── Market watch ───────────────────────────────────────────
  const priorityIds = ['jamaica','trinidad_tobago','barbados','guyana','bahamas','cayman'];
  const marketById: Record<string, any> = Object.fromEntries(markets.map((m: any) => [m.id, m]));
  const orderedMarkets = priorityIds.map(id => marketById[id]).filter(Boolean);
  const statusLabels: Record<string, string> = {
    official_source_identified: 'Official source identified',
    proxy_watch: 'Proxy watch',
    live: 'Live feed',
    planned: 'Feed planned',
  };

  let marketWatchHtml = '';
  let marketChartHtml = '';
  let sourceRegistryHtml = '';

  for (const m of orderedMarkets) {
    const ex = m.exchange || {};
    const status = statusLabels[ex.feed_status] ?? (ex.feed_status || 'Feed planned').replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
    const statusClass = ex.feed_status === 'proxy_watch' ? 'proxy' : 'official';
    const sectors = ((m.watch_sectors || []) as string[]).slice(0, 4).join(', ');
    const news = ((m.credible_news || []) as any[]).slice(0, 3).map((n: any) => n.name || '').join(', ');
    const links = ((m.signal_links || []) as string[]).slice(0, 4).join(', ');
    const fx = m.fx || {};
    const snap = m.market_snapshot || {};
    const bars = ((snap.bars || []) as number[]).slice(0, 8)
      .map((v: number) => `<i style="height:${Math.max(8, Math.min(100, v || 0))}%"></i>`).join('');
    const exchName = ex.name || 'Market source';
    const exchHtml = ex.url
      ? `<a href="${esc(ex.url)}" target="_blank" rel="noopener">${esc(exchName)}</a>`
      : esc(exchName);
    marketWatchHtml += `<article class="market-card ${statusClass}">
      <div class="market-top"><span class="market-code">${esc(ex.code || '—')}</span><span class="market-status">${esc(status)}</span></div>
      <h3>${esc(m.country || 'Market')}</h3>
      <p class="market-exchange">${exchHtml}</p>
      <div class="market-finance-row"><span>FX ${esc(fx.pair || '—')}</span><span>${esc(fx.rate_label || 'watch')}</span></div>
      <p><strong>Watch:</strong> ${esc(sectors)}</p>
      <p><strong>News context:</strong> ${esc(news)}</p>
      <p><strong>Linked signals:</strong> ${esc(links)}</p>
    </article>`;
    marketChartHtml += `<article class="market-chart-card ${statusClass}">
      <div class="market-top"><span class="market-code">${esc(ex.code || '—')}</span><span class="market-status">${esc(snap.data_status || status)}</span></div>
      <h3>${esc(snap.headline || exchName)}</h3>
      <div class="mini-bars" aria-label="${esc(snap.chart_label || 'Market activity proxy')}">${bars}</div>
      <p><strong>${esc(snap.chart_label || 'Market activity proxy')}</strong></p>
      <p>${esc(snap.focus || 'Market notices and official source updates')}</p>
      <div class="market-finance-row"><span>${esc(fx.indicator || 'FX watch')}</span><span>${esc(fx.pair || '—')}</span></div>
    </article>`;
  }

  const regionalSources: any[] = marketSources.regional_context_sources || [];
  const regionalSourceHtml = regionalSources.slice(0, 10)
    .map((src: any) => `<span>${esc(src.name || '')}</span>`).join('');
  const marketDataSources: any[] = marketSources.market_data_sources || [];
  const fxSources: any[] = marketSources.fx_sources || [];
  const registryGroups = [
    ['Official market data', marketDataSources],
    ['FX / currency', fxSources],
    ['Regional context', regionalSources],
  ] as [string, any[]][];
  for (const [label, sources] of registryGroups) {
    const chips = sources.map((src: any) =>
      `<a href="${esc(src.url || '#')}" target="_blank" rel="noopener">${src.code ? esc(src.code) + ' · ' : ''}${esc(src.name || '')}</a>`
    ).join('');
    sourceRegistryHtml += `<div class="source-registry-group"><strong>${esc(label)}</strong><div>${chips}</div></div>`;
  }

  // ── All clusters (audit) ───────────────────────────────────
  // fallow-ignore-next-line complexity
  const allClustersHtml = clusters.map((c, i) => {
    const ct = cleanSignalTitle(c.title || '');
    const cc = c.country_cluster || '';
    const cg = cleanGrade(c.evidence_grade || '');
    const cf = c.freshness || '';
    const cd = (c.decision || '').slice(0, 100);
    const ce = cleanEvidence(c.evidence || '');
    const cr: string[] = c.risk_flags || [];
    const crHtml = cr.length ? `<div class="risk-inline">⚠️ ${esc(cr[0].slice(0, 80))}</div>` : '';
    const routesHtml = ((c.personas || []) as any[]).slice(0, 3)
      .map((r: any) => `<div class="route-line"><span>${esc(r.persona || '')}</span> <span>${esc(r.channel || '')}</span></div>`)
      .join('');
    return `<div class="cluster-card">
      <div class="cnum">${String(i + 1).padStart(2, '0')}</div>
      <div class="cbody">
        <h4>${esc(ct)}${cc ? ' · ' + esc(cc) : ''}</h4>
        <div class="conf-badge conf-high">${esc(cg)} · ${esc(cf)}</div>
        <p><strong>Decision:</strong> ${esc(cd)}</p>
        <p><strong>Evidence:</strong> ${esc(ce)}</p>
        ${crHtml}
        <div class="croutes">${routesHtml}</div>
      </div>
    </div>`;
  }).join('');

  // ── Thesis + counts ────────────────────────────────────────
  const thesis = readText('outbox/regional_thesis.md');
  // fallow-ignore-next-line complexity
  const thesisLine = thesis.split('\n').find(l => {
    const t = l.trim();
    return t && !t.startsWith('#') && !t.startsWith('**') && !t.startsWith('Generated') && t.length > 20;
  })?.trim() || '';

  const nClusters = clusters.length;
  const nComposite = ((readJson('data/composite/latest.json') || {}).signals || []).length;
  const nPersonas = desk.dispatch_count || 0;
  const nFb = fbHist.length;
  const nCountries = Object.keys(COUNTRY_COORDS).length;
  const nowStr = new Date().toLocaleString('en-US', { month:'long', day:'numeric', year:'numeric', hour:'2-digit', minute:'2-digit', timeZone:'UTC' }) + ' UTC';

  // ── Replay JSONL ───────────────────────────────────────────
  let replayJsonlUrl = '';
  const histDir = join(ROOT, 'data/history');
  if (existsSync(histDir)) {
    try {
      const files = readdirSync(histDir)
        .filter(f => f.endsWith('.jsonl'))
        .map(f => ({ f, mtime: statSync(join(histDir, f)).mtime.getTime() }))
        .sort((a, b) => b.mtime - a.mtime);
      if (files.length) replayJsonlUrl = `/data/history/${files[0].f}`;
    } catch {}
  }

  // ── Analyst JS blob ────────────────────────────────────────
  const analystData = {
    cycle: cycleId,
    lead: {
      title: lTitle, country: lCountry, evidence: lEvidence,
      decision: lDecision, pct: leadPctStr, risks: lRisks,
      personas: pcards.slice(0, 4).map(([persona, channel, action]) => ({ persona, channel, action })),
    },
    thesis: thesisLine.slice(0, 300),
    sources: nSources, signals: nComposite, dispatches: nPersonas,
  };

  const verdictCounts = {
    all: advanceCount + holdCount + rejectCount,
    advance: advanceCount, hold: holdCount, reject: rejectCount,
  };

  return {
    // Scalars
    cycleId, nowStr, nCountries, nSources, nClusters, nPersonas, nFb, nComposite,
    // Lead signal
    lTitle, lCountry, lEvidence, lRanking, lDecision, lGrade, lRisks, leadPctStr,
    leadAction, leadWindow, leadOwner, leadDispatchId, leadDelivery, leadFeedback, leadRationale,
    // HTML fragments
    leadRoutesHtml, validationPackHtml, secSignals, receiptsHtml, boostsHtml,
    receiptsProvenanceHtml, marketWatchHtml, marketChartHtml, regionalSourceHtml,
    sourceRegistryHtml, allClustersHtml, fbActionPills,
    srcRows,
    // Counts
    marketSourceCount: marketDataSources.length,
    fxSourceCount: fxSources.length,
    verdictCounts,
    // JSON blobs (embedded in <script>)
    analystData: JSON.stringify(analystData).replace(/<\//g, '<\\/'),
    mapMarkersJson: JSON.stringify(mapMarkers).replace(/<\//g, '<\\/'),
    mapDispatchesJson: JSON.stringify(mapDispatches).replace(/<\//g, '<\\/'),
    allPacksJson: JSON.stringify(allPacks).replace(/<\//g, '<\\/'),
    verdictCountsJson: JSON.stringify(verdictCounts),
    lRisksJson: JSON.stringify(lRisks),
    replayJsonlUrl: replayJsonlUrl.replace(/<\//g, '<\\/'),
    humanizeRulesJson,
    tickerHtml, frontPointersHtml,
    // Ticker items for client-side lw-rail width calculation
    tickerItemCount: tickerItems.length,
  };
}
