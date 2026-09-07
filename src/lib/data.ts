// Port of dashboard/generate.py data loading + transformation.
// Runs at Astro build time (Node.js); reads JSON files from the repo root.

import { readFileSync, existsSync, readdirSync, statSync } from 'fs';
import { resolve, join } from 'path';
import { humanize, humanizeRulesJson, cleanHeadline, cleanDek, humanizeStatus, statusChip } from './humanize.ts';

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
/** "2026-08-30" -> "30 Aug 2026". Falls back to the raw value if unparseable. */
function friendlyDate(iso: string): string {
  const dt = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(dt.getTime())) return iso;
  return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}

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

/**
 * The lead headline. "All signals point to X" is only honest when more than
 * one source actually confirms X — the desk's own evidence grade says how
 * many do, so the headline follows it rather than asserting consensus that
 * a single-source signal does not have.
 */
function cleanTitle(raw: string, evidenceGrade = ''): string {
  const country = raw.includes(':') ? raw.split(':')[0].trim() : 'Caribbean';
  const grade = evidenceGrade.toLowerCase();
  const corroborated = grade.includes('multi-source') || grade.includes('cross-source')
    || evidenceGrade.startsWith('A') || evidenceGrade.startsWith('B');
  return corroborated
    ? `All signals point to ${country}.`
    : `${country} is the one to watch.`;
}

// fallow-ignore-next-line complexity
function cleanGrade(raw: string): string {
  const r = raw.toLowerCase();
  if (r.includes('multi-source') || raw.startsWith('A')) return 'Solid: several sources agree';
  if (r.includes('cross-source') || raw.startsWith('B')) return 'Promising: more than one source';
  if (raw.startsWith('C')) return 'Early: one source so far';
  return 'Exploratory';
}

function cleanEvidence(raw: string): string {
  return raw
    .replace(/WB\s+/g, 'World Bank ')
    .replace(/detected:\s*/g, 'data shows: ')
    .replace(/FDI surge/g, 'FDI movement')
    // "1 regional dataset(s)" — pick the plural the count actually calls for.
    // The noun is not always adjacent to the number ("1 regional dataset(s)"),
    // so carry the nearest preceding count across the words between them.
    .replace(/\b(\d+)([^;.]{0,40}?)\b([A-Za-z]+)\(s\)/g,
      (_m, n, mid, word) => `${n}${mid}${word}${Number(n) === 1 ? '' : 's'}`);
}

/** Evidence arrives as one semicolon-joined run-on. Readers get a list. */
function evidenceListHtml(raw: string): string {
  const parts = cleanEvidence(raw)
    .split(';')
    .map(part => part.replace(/^[\s•\-–]+/, '').trim())
    .filter(part => part.length > 1);
  if (!parts.length) return '';
  if (parts.length === 1) return `<p><strong>Evidence:</strong> ${esc(humanize(parts[0]))}</p>`;
  return `<p class="evidence-lead"><strong>Evidence</strong></p><ul class="evidence-list">${
    parts.map(part => `<li>${esc(humanize(part))}</li>`).join('')}</ul>`;
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
  const KEY_ALIAS: Record<string, string> = {
    'trinidad and tobago': 'Trinidad & Tobago',
    'antigua and barbuda': 'Antigua & Barbuda',
    'st. lucia': 'St Lucia',
    'saint lucia': 'St Lucia',
    'st. kitts and nevis': 'St Kitts & Nevis',
    'st kitts and nevis': 'St Kitts & Nevis',
    'saint kitts and nevis': 'St Kitts & Nevis',
    'st. vincent and the grenadines': 'St Vincent & the Grenadines',
    'st vincent and the grenadines': 'St Vincent & the Grenadines',
    'saint vincent and the grenadines': 'St Vincent & the Grenadines',
    'turks and caicos': 'Turks & Caicos',
    'u.s. virgin islands': 'US Virgin Islands',
  };
  const trimmed = raw.trim();
  return ALIAS[trimmed] ?? KEY_ALIAS[trimmed.toLowerCase()] ?? trimmed;
}

// fallow-ignore-next-line complexity
function watchlistSignal(country: string, market: any, fx: any): any {
  const exchange = market?.exchange || {};
  const snapshot = market?.market_snapshot || {};
  if (market && Object.keys(market).length) {
    const code = exchange.code || 'market source';
    // snapshot.focus is sometimes an array of sectors; joining it here is
    // what keeps "banking,insurance,tourism" from reaching the page.
    const rawFocus = snapshot.focus;
    const focus = (Array.isArray(rawFocus) ? rawFocus.join(', ') : rawFocus)
      || (market.watch_sectors || []).slice(0, 3).join(', ')
      || 'official notices and local market context';
    return {
      confidence: 34,
      kind: 'market',
      summary: `Market watch: ${code} — watching ${focus}`,
      ranking_rationale: 'From the market watchlist. It becomes a live briefing once core data or a second source confirms movement.',
    };
  }
  if (fx?.pair) {
    return {
      confidence: 28,
      kind: 'market',
      summary: `Currency watch: ${fx.pair} ${fx.rate_label || ''} — keeping an eye on reserves, flows, and official notices`.replace(/\\s+/g, ' '),
      ranking_rationale: 'From FX and market coverage. It becomes a live briefing once a second source confirms movement.',
    };
  }
  return {
    confidence: 28,
    kind: 'market',
    summary: 'Watching official notices plus tourism and shipping activity for signs of movement',
    ranking_rationale: 'From regional market coverage. It becomes a live briefing once a second source confirms movement.',
  };
}

// ── Validation pack HTML builders ──────────────────────────

// fallow-ignore-next-line complexity
/**
 * Reader-facing meaning of a confidence score, from outbox/calibration.json.
 * The desk publishes a number every cycle; this says whether that number has
 * ever been checked against what actually happened. Until a band has enough
 * resolved claims we say so plainly rather than implying a probability.
 */
function calibrationNoteFor(score: number | string): string {
  const report = readJson('outbox/calibration.json');
  if (!report || !Array.isArray(report.bands)) {
    return 'Ranking position, not a probability — calibration not yet running.';
  }
  const value = Number(score);
  const band = report.bands.find((b: any) => {
    const [lo, hi] = String(b.band).split('-').map(Number);
    return Number.isFinite(value) && value >= lo && value <= hi;
  });
  if (band && band.confirmation_rate !== null && band.confirmation_rate !== undefined) {
    const pct = Math.round(Number(band.confirmation_rate) * 100);
    return `Calls this strong have held up ${pct}% of the time, across ${band.resolved} we have since followed up on.`;
  }
  const open = Number(report.open_claims || 0);
  return `Ranking position, not a probability — ${open} claim${open === 1 ? '' : 's'} still open, `
    + `${report.min_sample ?? 5} needed per band before a rate is published.`;
}

/**
 * The public accuracy commitment. Targets are published before the claims
 * resolve, so the page shows what was promised and how it is tracking —
 * including when a gate is missed.
 */
function calibrationCommitmentHtml(): string {
  const report = readJson('outbox/calibration.json');
  const gates: any[] = (report && report.commitments) || [];
  if (!gates.length) return '';
  const rows = gates.map((g: any) => {
    const target = [`${g.min_resolved} resolved`, g.max_brier ? `Brier ≤ ${g.max_brier}` : '']
      .filter(Boolean).join(' · ');
    return `<tr>
      <td>${esc(g.milestone)}</td>
      <td>${esc(target)}</td>
      <td><span class="commit-status commit-${esc(g.status)}">${esc(g.status)}</span></td>
    </tr>`;
  }).join('');
  const brier = report.brier === null || report.brier === undefined ? 'not yet scored' : report.brier;
  const chain = report.chain_intact ? 'ledger chain intact' : '⚠ LEDGER CHAIN BROKEN';
  return `<div class="calibration-commitment">
    <div class="commit-head">
      <strong>Accuracy we committed to on ${esc(report.committed_at || '—')}</strong>
      <span>${esc(report.total_resolved ?? 0)} resolved · ${esc(report.open_claims ?? 0)} open · Brier ${esc(brier)} · ${esc(chain)}</span>
    </div>
    <table class="commit-table"><tbody>${rows}</tbody></table>
    <p class="commit-note">Published before the calls resolve. A missed gate stays on this page.</p>
  </div>`;
}

function packFreshnessStrip(pack: any): string {
  const freshness = pack.evidence_freshness || 'unknown';
  const cycles = parseInt(pack.cycles_since_refresh || '0', 10) || 0;
  const readiness = pack.action_readiness || 'n/a';
  const calibrated = pack.confidence_score ?? '—';
  const validated = age(pack.last_validated_at);
  const labelMap: Record<string, string> = { refreshing:'Still coming in', aging:'Getting older', stale:'Going cold' };
  const label = labelMap[freshness] ?? freshness.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
  const cycleNote = cycles === 0 ? 'something new came in today' : `nothing new for ${cycles} cycle${cycles === 1 ? '' : 's'}`;
  // `raw` is the uncapped internal score used for ranking. It means nothing to a
  // reader beside the 0-100 figure, so it stays out of the page.
  const readinessMap: Record<string, string> = {
    high: 'Ready to act on', medium: 'Worth a look', low: 'Early — keep watching',
  };
  const readinessLabel = readinessMap[String(readiness).toLowerCase()] ?? readiness;
  return `<div class="vpack-freshness">
    <span class="freshness-pill ${esc(freshness)}">${esc(label)}</span>
    <span class="freshness-meta">${esc(readinessLabel)}</span>
    <span class="freshness-meta">Confidence <strong>${esc(calibrated)}</strong> out of 100</span>
    <span class="freshness-meta">Checked ${esc(validated)} · ${esc(cycleNote)}</span>
    <span class="freshness-meta freshness-calibration">${esc(calibrationNoteFor(calibrated))}</span>
  </div>`;
}

// fallow-ignore-next-line complexity
const NOW_YEAR = new Date().getUTCFullYear();

/** Pipeline records are loosely typed; normalise a field to a string once. */
const str = (v: any): string => String(v ?? '');
/** Every 4-digit year in a blob of text, ignoring anything in the future. */
const yearsIn = (text: string): number[] =>
  (text.match(/(19|20)\d{2}/g) || []).map(Number).filter(y => y <= NOW_YEAR);

const HYP_STATUS_LABEL: Record<string, string> = {
  corroborated: 'Confirmed',
  unconfirmed: 'Not confirmed yet',
  contradicted: 'Contradicted',
  // Without this the badge fell through to the raw token, "macro signal".
  macro_signal: 'Whole-economy figure',
};

// Packs generated before the wording was fixed still carry the old label, and
// they stay on the site until the next cycle regenerates them.
const LEGACY_SECTOR_COPY: Record<string, string> = {
  'FDI-receiving sectors (composition not yet broken down)':
    'Which industries received it is not published yet',
};

function packHypothesisLi(h: any): string {
  // The class keeps the raw token for styling; the label is what a reader sees.
  const status = str(h.status);
  const label = HYP_STATUS_LABEL[status] || status.replace(/_/g, ' ');
  const badge = status ? `<span class="hyp-status ${esc(status)}">${esc(label)}</span>` : '';
  const basis = h.basis ? `<em>${esc(humanize(h.basis))}</em>` : '';
  const sector = str(h.sector);
  return `<li><strong>${esc(LEGACY_SECTOR_COPY[sector] || sector)}</strong>${badge}${basis}</li>`;
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
  // Supporting projects arrive with no date field; the year is only ever in the
  // title ("Guyana Labor Force Survey: Third Quarter 2017"). Listed undated
  // under "today's call" a 2013 survey reads as evidence for a move that
  // happened last month, so pull the year out and separate current evidence
  // from background.
  const projectYear = (p: any): number | null => {
    const years = yearsIn([p.date, p.approval_date, p.year, p.title].map(str).join(' '));
    return years.length ? Math.max(...years) : null;
  };
  const yearTag = (year: number | null) => (year ? `<span class="vpack-year">${year}</span>` : '');
  const projectLi = (p: any, year: number | null) => {
    const title = esc(str(p.title).slice(0, 90));
    const meta = `${yearTag(year)}<em>${esc(str(p.source))}</em>`;
    const url = str(p.url);
    return url
      ? `<li><a href="${esc(url)}" target="_blank" rel="noopener">${title}</a>${meta}</li>`
      : `<li>${title}${meta}</li>`;
  };
  const allProjects = ((pack.supporting_projects || []) as any[])
    .map((p: any) => ({ p, year: projectYear(p) }));
  const currentProjects = allProjects.filter(x => x.year === null || x.year >= NOW_YEAR - 2);
  const olderProjects = allProjects.filter(x => x.year !== null && x.year < NOW_YEAR - 2);
  const projLis = (currentProjects.slice(0, 4).map(x => projectLi(x.p, x.year)).join('')
    || '<li class="vpack-empty">Nothing current matched this cycle.</li>')
    + (olderProjects.length
      ? `<li class="vpack-older"><details><summary>${olderProjects.length} older item${olderProjects.length === 1 ? '' : 's'} for background</summary><ul>${olderProjects.slice(0, 4).map(x => projectLi(x.p, x.year)).join('')}</ul></details></li>`
      : '');
  const procLis = ((pack.procurement_matches || []) as any[]).slice(0, 4).map((p: any) => packProcurementLi(p)).join('')
    || '<li>No live procurement notices matched.</li>';
  const qLis = ((pack.unresolved_questions || []) as any[]).slice(0, 4)
    .map((q: any) => `<li>${esc(humanize(q))}</li>`).join('');

  return `<div class="vpack">
    <div class="vpack-head">
      <div>
        <span>What we checked</span>
        <h3>What the system already checked for ${esc(pack.country || country)}</h3>
      </div>
      <span class="vpack-verdict ${esc(verdict)}">${esc(verdictLabel)}</span>
    </div>
    <details class="meta-disclose"><summary>How this was scored</summary><div class="meta-disclose-body">
      ${packFreshnessStrip(pack)}
      <div class="vpack-reason">${esc(humanize(pack.recommendation_reason || ''))}</div>
    </div></details>
    <div class="vpack-grid">
      <div class="vpack-col"><h4>Which industries</h4><ul>${hypLis}</ul></div>
      <div class="vpack-col"><h4>Companies on the ground</h4><ul>${opLis}</ul></div>
      <div class="vpack-col"><h4>Projects backing it up</h4><ul>${projLis}</ul></div>
      <div class="vpack-col"><h4>Live tenders</h4><ul>${procLis}</ul></div>
    </div>
    <div class="vpack-questions"><h4>Still open — what to check this week</h4><ul>${qLis}</ul></div>
  </div>`;
}

// Cycle ids look like 20260825. Printed raw they read as a barcode, so the page
// shows the date and keeps the id in a title attribute for traceability.
const RECENT_DAY_LABEL: Record<number, string> = { 0: 'Today', 1: 'Yesterday' };

function cycleDateLabel(id: string): string {
  const raw = String(id);
  const m = raw.match(/^(\d{4})(\d{2})(\d{2})/);
  if (!m) return raw;
  const dt = new Date(`${m[1]}-${m[2]}-${m[3]}T00:00:00Z`);
  if (Number.isNaN(dt.getTime())) return raw;
  const now = new Date();
  const days = Math.round(
    (Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()) - dt.getTime()) / 86400000);
  return RECENT_DAY_LABEL[days]
    || dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });
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
          <span>What we checked</span>
          <h4>Evidence for ${esc(pack.country || cc)}</h4>
          <span class="sig-validation-verdict ${esc(verdict)}">${esc(vl)}</span>
        </div>
        <div class="sig-freshness">
          <span class="freshness-pill ${esc(fresh)}">${esc(freshLabel)}</span>
          <span class="freshness-meta">${esc(pack.action_readiness || 'n/a')} · ${esc(String(cycles))} cycles stale · conf ${esc(pack.confidence_score ?? '—')}</span>
        </div>
        <div class="sig-validation-grid">
          <div class="sig-validation-col"><h5>Which industries</h5><ul>${hypLis}</ul></div>
          <div class="sig-validation-col"><h5>Projects &amp; data</h5><ul>${projLis}</ul></div>
          <div class="sig-validation-col"><h5>Live tenders</h5><ul>${procLis}</ul></div>
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
        <span class="art-by" title="Cycle ${esc(cycleId)}">By the Desk · ${esc(cycleDateLabel(cycleId))}</span>
      </div></div>
      ${riskHtml}
      <span class="sig-expand" aria-label="Expand validation" title="View validation pack">▼</span>
      ${validationHtml}
    </div>`,
  };
}

// ── Branded indexed activity renderer ──────────────────────
//
// `snap.bars` is a single indexed value per period (0-100). It used to be
// drawn as OHLC candlesticks, which meant inventing three of the four values
// each candle needs — the highs and lows came from `index % 3`, and the
// tooltip then read them out as though they were observations. A one-value
// series gets a one-value mark: a column per period, coloured by its
// direction against the previous period, which is the only comparison the
// data actually supports.

function buildIndexedActivitySvg(values: number[], label: string): string {
  const points = values.slice(0, 8).map(v => Math.max(0, Math.min(100, Number(v) || 0)));
  if (!points.length) return '';
  const width = 320, height = 126, plotLeft = 14, plotRight = 286, plotTop = 14, plotBottom = 102;
  const y = (value: number) => plotTop + (100 - value) / 100 * (plotBottom - plotTop);
  const step = (plotRight - plotLeft) / Math.max(points.length, 1);
  const grid = [0, 25, 50, 75, 100].map(value => {
    const yy = y(value).toFixed(1);
    return `<line class="activity-grid-line" x1="${plotLeft}" y1="${yy}" x2="${plotRight}" y2="${yy}" />`;
  }).join('');
  const axis = [100, 50, 0].map(value => `<text class="activity-axis-label" x="312" y="${(y(value) + 3).toFixed(1)}" text-anchor="end">${value}</text>`).join('');
  const columns = points.map((value, index) => {
    const previous = index === 0 ? null : points[index - 1];
    const delta = previous === null ? 0 : value - previous;
    const state = index === points.length - 1 ? 'latest' : '';
    const x = plotLeft + step * index + step / 2;
    const barWidth = Math.min(16, step * .48);
    const top = y(value);
    const move = previous === null
      ? 'first period shown'
      : delta === 0 ? 'unchanged from the previous period'
      : `${delta > 0 ? 'up' : 'down'} ${Math.abs(Math.round(delta))} from the previous period`;
    return `<g class="activity-col ${state}" tabindex="0"><title>Period ${index + 1}: activity ${Math.round(value)} of 100 — ${move}. Not a price.</title><rect class="activity-bar" x="${(x - barWidth / 2).toFixed(1)}" y="${top.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${Math.max(2, plotBottom - top).toFixed(1)}" /><circle class="activity-node" cx="${x.toFixed(1)}" cy="${top.toFixed(1)}" r="2.1" /></g>`;
  }).join('');
  const latest = points[points.length - 1];
  const latestY = y(latest).toFixed(1);
  return `<svg class="activity-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(label)}. Activity level per period on a 0 to 100 scale. Not a share price."><title>${esc(label)} — activity trend, not a share price</title>${grid}<line class="activity-baseline" x1="${plotLeft}" y1="${plotBottom}" x2="${plotRight}" y2="${plotBottom}" />${columns}<line class="activity-latest-line" x1="${plotLeft}" y1="${latestY}" x2="${plotRight}" y2="${latestY}" /><circle class="activity-latest-dot" cx="${plotRight}" cy="${latestY}" r="3.5" />${axis}<text class="activity-index-label" x="${plotLeft}" y="120">ACTIVITY TREND · NOT A SHARE PRICE</text></svg>`;
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
  // Markets: prefer data/market_watch/latest.json (rich, generated by the
  // poller), then public/market_watch.json (Vercel build-context copy),
  // then the bare config. Vercel build context excludes data/* by default
  // so we keep the public/ copy in sync; for local dev both files exist.
  const pollerSnapshot = readJson('data/market_watch/latest.json') ||
                         readJson('public/market_watch.json') ||
                         readJson('api/market-watch-data.json');
  const markets: any[] = (pollerSnapshot && pollerSnapshot.markets) || marketSources.markets || [];
  const regionalNewsData = readJson('public/regional_news.json') || readJson('data/regional_news/latest.json') || {};
  const rawNews: any[] = regionalNewsData.items || [];
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
    const snap = m.market_snapshot || {};
    // The drill panel interpolates these straight into a tagged template,
    // which concatenates array items with no separator at all.
    return Array.isArray(snap.focus) ? { ...snap, focus: snap.focus.join(', ') } : snap;
  }

  // ── Regional news intelligence ──────────────────────────────
  const NEWS_TOPICS: Record<string, string[]> = {
    finance:['bank','finance','currency','exchange','credit','inflation','investment','fdi','fund'],
    energy:['oil','gas','energy','renewable','electricity','solar'],
    tourism:['tourism','hotel','visitor','airlift','cruise'],
    trade:['trade','export','import','port','shipping','logistics','supply chain'],
    procurement:['procurement','tender','contract','project','infrastructure'],
    climate:['climate','storm','hurricane','flood','drought','weather'],
  };
  const newsItems = rawNews.map((item: any) => {
    const text = `${item.title || ''} ${item.summary || ''}`.toLowerCase();
    const topics = item.topics?.length ? item.topics : Object.entries(NEWS_TOPICS)
      .filter(([, terms]) => terms.some(term => text.includes(term))).map(([topic]) => topic);
    const countries = (item.countries || []).map(canonicalCountry);
    // Recompute age at BUILD time from the published timestamp. The
    // poller's serialized age_hours was true when IT ran; trusting it on
    // later rebuilds froze articles as "20h ago" forever (Codex P2).
    const parsedAge = (() => { const t = Date.parse(item.published || ''); return Number.isFinite(t) ? Math.max(0, Math.floor((Date.now() - t) / 3600000)) : null; })();
    const ageHours = parsedAge ?? (typeof item.age_hours === 'number' ? item.age_hours : null);
    const tier = item.source_tier || (String(item.feed_slug || '').startsWith('google-news') ? 3 : 2);
    const score = Math.max(0, Math.min(100, 25 + (4-tier)*8 + topics.length*6 + countries.length*6 + (ageHours === null ? 0 : ageHours <= 24 ? 28 : ageHours <= 72 ? 18 : ageHours <= 168 ? 8 : 0)));
    return { ...item, countries, topics: topics.length ? topics : ['regional'], age_hours: ageHours, source_tier:tier, relevance_score:score };
  }).sort((a: any, b: any) => b.relevance_score - a.relevance_score || String(b.published || '').localeCompare(String(a.published || '')));
  const regionalContext = newsItems.filter((item: any) => !item.countries.length).slice(0, 3);
  function newsForCountry(country: string): { coverage: string; items: any[] } {
    const direct = newsItems.filter((item: any) => item.countries.includes(country))
      .sort((a: any, b: any) => Number(String(b.title || '').toLowerCase().includes(country.toLowerCase())) - Number(String(a.title || '').toLowerCase().includes(country.toLowerCase())) || b.relevance_score - a.relevance_score);
    return direct.length ? { coverage:'Country mentioned in coverage', items:direct.slice(0, 3) }
      : { coverage:'Regional context — no direct country match', items:regionalContext.slice(0, 2) };
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
    const market = marketProfileFor(country);
    const fx = fxProfileFor(country);
    const watch = c.signal_kind ? {} : watchlistSignal(country, market, fx);
    const countryNews = newsForCountry(country);
    const financeNews = countryNews.items.find((item: any) => String(item.title || '').toLowerCase().includes(country.toLowerCase()) && (item.finance_relevant || item.topics.some((t: string) => ['finance','energy','trade','procurement','tourism'].includes(t))));
    // Evidence mix: count only source families explicitly named in the
    // cluster's evidence. Do not infer IDB from "multi-source", or assign
    // World Bank to a watchlist by default: those shortcuts make the UI
    // claim provenance the source artifact never supplied.
    const evidenceText = [
      c.evidence,
      c.evidence_summary,
      ...(Array.isArray(c.sources) ? c.sources : []),
      ...(Array.isArray(c.source_labels) ? c.source_labels : []),
    ].filter(Boolean).join(' ').toLowerCase();
    const evidenceMix = (() => {
      const m = { wb: 0, idb: 0, noaa: 0, ndbc: 0, caricom: 0, cdb: 0 };
      if (/\bworld bank\b|\bwb\b/.test(evidenceText)) m.wb = 1;
      if (/\binter-american development bank\b|\bidb\b/.test(evidenceText)) m.idb = 1;
      if (/\bnational oceanic and atmospheric administration\b|\bnoaa\b/.test(evidenceText)) m.noaa = 1;
      if (/\bnational data buoy center\b|\bndbc\b/.test(evidenceText)) m.ndbc = 1;
      if (/\bcaribbean community\b|\bcaricom\b/.test(evidenceText)) m.caricom = 1;
      if (/\bcaribbean development bank\b|\bcdb\b/.test(evidenceText)) m.cdb = 1;
      return m;
    })();

    // Source status: active dispatches use the desk publication timestamp;
    // watchlist-only entries use their market observation. These are named
    // separately in the UI so publication recency is never presented as an
    // underlying evidence-observation timestamp.
    const normalizeDeskTimestamp = (raw: any, cycleId: any): string => {
      const value = String(raw || '').trim();
      if (value) {
        const normalized = value
          .replace(/ UTC$/i, 'Z')
          .replace(/^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})Z$/, '$1T$2:00Z');
        if (Number.isFinite(Date.parse(normalized))) return new Date(normalized).toISOString();
      }
      const cycle = String(cycleId || '');
      if (/^\d{8}$/.test(cycle)) {
        return `${cycle.slice(0, 4)}-${cycle.slice(4, 6)}-${cycle.slice(6, 8)}T00:00:00.000Z`;
      }
      return '';
    };
    const signalObservedAt = normalizeDeskTimestamp(desk.generated_at, desk.cycle_id);
    const marketObservedAt = String(
      (market && market.observation_at)
      || (market && market.market_snapshot && market.market_snapshot.observation_at)
      || '',
    );
    const observedAt = c.signal_kind ? signalObservedAt : marketObservedAt;
    const signalAgeHours = signalObservedAt
      ? Math.max(0, (Date.now() - Date.parse(signalObservedAt)) / 3_600_000)
      : Number.POSITIVE_INFINITY;
    const signalFreshnessState = signalAgeHours <= 6
      ? 'current'
      : signalAgeHours <= 24
        ? 'delayed'
        : 'stale';
    const marketFreshnessState = (market && market.freshness_state)
      || (market && market.market_snapshot && market.market_snapshot.data_status)
      || watch.freshness_state
      || 'source_checked_no_dated_observation';
    const freshnessState = c.signal_kind ? signalFreshnessState : marketFreshnessState;
    const lifecycle = (() => {
      const lastSeen = observedAt ? observedAt.slice(0, 10) : 'unknown';
      const hasTime = observedAt.length > 10 && observedAt.includes('T');
      const lastSeenTime = hasTime ? `${observedAt.slice(11, 16)} UTC` : '';
      return {
        last_seen: lastSeenTime ? `${lastSeen} ${lastSeenTime}` : lastSeen,
        cadence: desk.cycle_id ? `Scheduled every 4h · cycle ${desk.cycle_id}` : 'Scheduled every 4h',
        scope: c.signal_kind ? 'Dispatch desk' : 'Market watch',
        time_label: c.signal_kind ? 'Published' : 'Observed',
        freshness: freshnessState === 'current'
          ? 'fresh'
          : freshnessState === 'delayed'
            ? 'aging'
            : 'stale',
      };
    })();
    return {
      country, lat, lng,
      confidence: c.confidence_score || watch.confidence || 0,
      kind: c.signal_kind ? (c.signal_kind.includes('invest') ? 'investment'
        : c.signal_kind.includes('climate') || c.signal_kind.includes('weather') || c.signal_kind.includes('vulnerability') || c.signal_kind.includes('food_security') ? 'climate'
        : c.signal_kind.includes('procure') || c.signal_kind.includes('pipeline') ? 'procurement'
        : 'none') : watch.kind || 'none',
      track: c.track === 'opportunity' || c.track === 'risk' ? c.track : 'unclassified',
      summary: humanize(c.top_signal_summary || c.title || c.decision || watch.summary || ''),
      ranking_rationale: humanize(c.ranking_rationale || watch.ranking_rationale || ''),
      finance_signal: financeNews ? `${countryNews.coverage}: ${financeNews.title}` : (fx.signal || 'Monitor official financial and market notices'),
      news_coverage: countryNews.coverage,
      news: countryNews.items.map((item: any) => ({ title:item.title, url:item.url, source:item.source, published:item.published, topics:item.topics })),
      fx,
      evidence_mix: evidenceMix,
      lifecycle,
      freshness_state: freshnessState,
      market: {
        code: (market.exchange || {}).code || '',
        name: (market.exchange || {}).name || '',
        status: (market.exchange || {}).feed_status || '',
        snapshot: snapshotFor(country),
      },
    };
  });

  // ── Regional movement strip ─────────────────────────────────
  // One chip per country with an active signal (confidence > 0 OR has
  // an evidence mix entry). The chip shows the country, its source-status
  // class, and a bounded confidence bar using the signal-kind palette.
  // Tapping a chip opens the map-drill for that country.
  function freshnessClass(state: string): 'fresh' | 'aging' | 'stale' {
    if (state === 'current' || state === 'fresh') return 'fresh';
    if (state === 'delayed' || state === 'aging') return 'aging';
    return 'stale';
  }

  const regionalMovementItems = mapMarkers
    .filter((m: any) => (m.confidence || 0) > 0 || (m.evidence_mix && Object.values(m.evidence_mix).reduce((a: number, b: any) => a + (Number(b) || 0), 0) > 0))
    .map((m: any) => {
      const cls = freshnessClass(m.freshness_state || '');
      const rawConfidence = Number(m.confidence);
      const conf = Number.isFinite(rawConfidence)
        ? Math.max(0, Math.min(100, rawConfidence))
        : 0;
      const totalEv = (m.evidence_mix ? Object.values(m.evidence_mix).reduce((a: number, b: any) => a + (Number(b) || 0), 0) : 0);
      const confColor = kindColor(m.kind || '');
      // Chips sit in a fixed-width grid, so the visible text stays terse —
      // the full reading lives in the title and the bar's aria-label.
      const evidence = totalEv > 0
        ? `${totalEv} source group${totalEv === 1 ? '' : 's'}`
        : 'watchlist';
      return `<button class="rmv-chip" data-country="${esc(m.country)}" data-freshness="${cls}" data-track="${esc(m.track || 'unclassified')}" title="${esc(m.country)} — ${cls}, confidence ${conf}/100, ${evidence}">
        <span class="rmv-name">${esc(m.country)}</span>
        <span class="rmv-bar" role="img" aria-label="Confidence: ${conf} of 100">
          <span class="rmv-bar-fill" style="width:${conf}%; background:${confColor}"></span>
        </span>
        <span class="rmv-meta">${conf}</span>
        <span class="rmv-state">${cls}</span>
      </button>`;
    }).join('');

  const regionalMovementHtml = regionalMovementItems
    ? `<div class="rmv-strip">${regionalMovementItems}</div>`
    : '<p class="muted">No active signals this cycle.</p>';

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
  // Dedupe again on the rendered headline, not just signal_id: separate signals
  // routinely humanize to the same sentence ("Early signal in Barbados — no
  // detail yet"), and the reader sees the sentence, not the id.
  // Two passes. First drop identical rendered headlines, then drop items that
  // are the same story told twice: same market, same figure. "Money is moving
  // into Guyana — up 860.3%" and "Foreign investment into Guyana is up 860.3%"
  // are one fact, and the wire should carry it once.
  const tickerSeenText = new Set<string>();
  const tickerSeenFact = new Set<string>();
  const tickerItems = Object.values(seenTicker)
    .sort((a, b) => (b.confidence_score || 0) - (a.confidence_score || 0))
    .filter((t: any) => {
      const country = canonicalCountry(t.country_cluster || '');
      const title = humanize(t.title || '');
      const textKey = `${country}|${title}`.toLowerCase();
      if (tickerSeenText.has(textKey)) return false;
      tickerSeenText.add(textKey);
      const figures = (title.match(/\d+(?:\.\d+)?/g) || []).join(',');
      const factKey = `${country}|${figures}`.toLowerCase();
      if (figures && tickerSeenFact.has(factKey)) return false;
      if (figures) tickerSeenFact.add(factKey);
      return true;
    })
    .slice(0, 12);

  // A headline on the wire is a dispatch, and every dispatch has its own page
  // (src/pages/signal/[id].astro builds one per entry of the same file these
  // items come from). Pointing the link there is what makes clicking a
  // headline open that headline — see the click handler note in index.astro.
  const dispatchHref = (t: any) =>
    t.dispatch_id ? `/signal/${encodeURIComponent(t.dispatch_id)}/` : '#front-page';

  // fallow-ignore-next-line complexity
  let tickerHtml = tickerItems.map((t: any) => {
    const color = kindColor(t.signal_kind || '');
    const country = canonicalCountry(t.country_cluster || '');
    const title = humanize(t.title || '');
    // A market with nothing behind it yet should not speak in the same voice as
    // a validated lead.
    const watchlist = /no detail yet/i.test(title);
    return `<a class="lw-item${watchlist ? ' lw-watch' : ''}" href="${esc(dispatchHref(t))}" data-country="${esc(country)}">` +
      `<i style="background:${color}"></i>` +
      `<span class="lw-kicker">${esc(t.country_cluster || 'Region')}</span>` +
      (watchlist ? '<span class="lw-tag">Watchlist</span>' : '') +
      `<span>${esc(title)}</span></a>`;
  }).join('');

  // ── Front pointers ─────────────────────────────────────────
  let frontPointersHtml = tickerItems.slice(1, 4).map((t: any) => {
    const country = canonicalCountry(t.country_cluster || '');
    return `<a class="fp-item" href="${esc(dispatchHref(t))}" data-country="${esc(country)}">` +
      `<span class="fp-kicker">${esc(t.country_cluster || 'Region')}</span>` +
      `<span class="fp-title">${esc(humanize(t.title || ''))}</span></a>`;
  }).join('');

  // ── Lead signal ────────────────────────────────────────────
  const lCountry = lead.country_cluster || 'Guyana';
  const lTitle = cleanTitle(lead.title || '', lead.evidence_grade || '');
  // Describe the ranking honestly. The old sentence asserted "evidence,
  // source coverage, movement size and feedback signals" for every lead,
  // including single-source ones where source coverage is exactly one.
  const leadGrade = String(lead.evidence_grade || '');
  const leadCorroborated = leadGrade.startsWith('A') || leadGrade.startsWith('B')
    || /multi-source|cross-source/i.test(leadGrade);
  const lRankingBasis = leadCorroborated
    ? `${lCountry} is the desk's lead this cycle. It is ahead of everything else on the wire for the size of the move, how much evidence backs it, and how many sources agree.`
    : `${lCountry} is the desk's lead this cycle, on the size of the move and how readers responded. Only one source confirms it so far — get a second, but don't wait to start looking.`;
  const lEvidence = humanize(cleanEvidence(lead.evidence || ''));
  const lRanking = humanize(lead.ranking_rationale || '')
    || 'We rank on how big the move is, how many sources agree, how much evidence sits behind it, and what readers did with it last time.';
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
        <div class="receipt-when" title="Cycle ${esc(rid)}"><strong>${esc(cycleDateLabel(rid))}</strong><span>${esc(cycleDate)}</span></div>
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

  // ── Regional news desk ─────────────────────────────────────
  // Relevance alone put a 2,353-day-old CDB booklet and a 2021 republished
  // notice on a desk headed "What is moving across the Caribbean". The country
  // drill already sorted around this; the desk itself did not. A year is well
  // past any reading of "moving" — items that old are archive, not news.
  const NEWS_MAX_AGE_HOURS = 365 * 24;
  // Relevance alone made a "Regional news desk" that was half one country —
  // nine of eighteen items were Jamaica, because Google News carries far more
  // Jamaican coverage than the rest of the region. api/regional-news.py already
  // caps this server-side (max 2 per publisher, 3 per country); the build-time
  // path that renders the page did not, so the two surfaces disagreed. Same
  // caps here, applied in relevance order so the best story per country wins.
  const NEWS_PER_PUBLISHER = 2;
  const NEWS_SLOTS = 18;
  const eligible = newsItems.filter((item: any) =>
    item.relevance_score >= 35 &&
    (item.age_hours === null || item.age_hours <= NEWS_MAX_AGE_HOURS));
  const countryOf = (item: any) => item.countries?.[0] || 'Regional context';
  const publisherOf = (item: any) =>
    item.publisher_name || item.publisher_domain || item.source || 'unknown';

  // Round-robin by country, relevance order preserved inside each round: every
  // country places its best story before any country places its second. Capping
  // and then topping the shelf back up does not work — where the feed is skewed
  // the top-up simply refills with the dominant country, which is how
  // production still opened eight-of-eighteen Jamaica after the first attempt.
  // This holds the spread at whatever shelf size the data can support.
  const byCountry = new Map<string, any[]>();
  for (const item of eligible) {
    const key = countryOf(item);
    if (!byCountry.has(key)) byCountry.set(key, []);
    byCountry.get(key)!.push(item);
  }
  const perPublisher = new Map<string, number>();
  const visibleNews: any[] = [];
  for (let round = 0; visibleNews.length < NEWS_SLOTS; round++) {
    const picks = [...byCountry.values()]
      .map(list => list[round])
      .filter(Boolean)
      .sort((a, b) => b.relevance_score - a.relevance_score);
    if (!picks.length) break;
    for (const item of picks) {
      if (visibleNews.length >= NEWS_SLOTS) break;
      // One publisher should not speak for several countries at once.
      const pub = publisherOf(item);
      if ((perPublisher.get(pub) ?? 0) >= NEWS_PER_PUBLISHER + round) continue;
      perPublisher.set(pub, (perPublisher.get(pub) ?? 0) + 1);
      visibleNews.push(item);
    }
  }

  const newsCountries = [...new Set(visibleNews.flatMap((item: any) => item.countries))].sort();
  const newsTopics = [...new Set(visibleNews.flatMap((item: any) => item.topics))].sort();

  // Country -> stories, so the map drill can show a country's news beside its
  // data instead of the three-link stub it carried before. Same source as the
  // news desk, so the two surfaces cannot disagree.
  const newsByCountry: Record<string, any[]> = {};
  for (const item of visibleNews) {
    const age = item.age_hours === null ? 'date unavailable'
      : item.age_hours < 24 ? `${item.age_hours}h ago`
      : `${Math.floor(item.age_hours / 24)}d ago`;
    for (const country of (item.countries.length ? item.countries : ['Regional context'])) {
      (newsByCountry[country] ||= []).push({
        title: cleanHeadline(item.title || ''),
        url: item.url,
        source: humanize(item.source || 'Regional source'),
        topic: (item.topics && item.topics[0]) || 'regional',
        tier: item.source_tier,
        ageHours: item.age_hours === null ? Number.MAX_SAFE_INTEGER : item.age_hours,
        age,
      });
    }
  }
  // The drill shows the first five, so freshest must lead — relevance order
  // alone let a six-year-old bank post outrank this week's coverage.
  for (const list of Object.values(newsByCountry)) list.sort((a, b) => a.ageHours - b.ageHours);
  // Topics stay in view; ~25 country chips would otherwise put a screen of
  // buttons between the reader and the first headline on mobile.
  const newsFilterHtml = [
    '<button class="news-filter active" data-news-filter="all">All</button>',
    ...newsTopics.map(topic => `<button class="news-filter" data-news-filter="topic:${esc(topic)}">${esc(topic)}</button>`),
    `<button class="news-filter news-filter-more" id="news-country-toggle" type="button" aria-expanded="false" aria-controls="news-countries">By country <span aria-hidden="true">+</span></button>`,
    `<span class="news-countries" id="news-countries" hidden>${newsCountries.map(country => `<button class="news-filter country" data-news-filter="country:${esc(country)}">${esc(country)}</button>`).join('')}</span>`,
  ].join('');
  const newsHtml = visibleNews.map((item: any, index: number) => {
    const countries = item.countries.length ? item.countries : ['Regional context'];
    const time = item.age_hours === null ? 'date unavailable' : item.age_hours < 24 ? `${item.age_hours}h ago` : `${Math.floor(item.age_hours / 24)}d ago`;
    const primaryCountry = countries[0] || 'Caribbean';
    const primaryTopic = (item.topics && item.topics[0]) || 'regional';
    const imageUrl = item.image_url || item.imageUrl || '';
    // Feed hygiene: de-shout notice headlines, strip CMS debris from the
    // summary, and drop the dek entirely when it only restates the headline.
    const headline = cleanHeadline(item.title || '');
    const isLead = index === 0;
    const dek = cleanDek(item.summary, headline, isLead ? 260 : 170);
    // The topic gradient is a stand-in picture, not a picture. It reads as
    // photography at a glance and there is nothing behind it, so it is now
    // reserved for the lead — every other story runs text-first and shows an
    // image only when the publisher actually gave us one.
    // Financial-editorial pass: every card carries a media block. Publisher
    // images win when present; otherwise the topic gradient stand-in gives
    // the board consistent visual rhythm instead of text-only rows.
    const showMedia = true;
    const mediaHtml = showMedia
      ? `<a class="news-media topic-${esc(primaryTopic)}" href="${esc(item.url)}" target="_blank" rel="noopener" aria-label="Read ${esc(headline)}">
        <span class="news-media-fallback" aria-hidden="true"><b>${esc(primaryCountry)}</b><em>${esc(primaryTopic)}</em></span>${imageUrl ? `<img class="news-image-backdrop" src="${esc(imageUrl)}" alt="" aria-hidden="true" loading="lazy" decoding="async" referrerpolicy="no-referrer"><img class="news-image-main" src="${esc(imageUrl)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="const media=this.closest('.news-media');media?.classList.add('image-failed');media?.querySelectorAll('img').forEach(img=>img.remove())">` : ''}
      </a>`
      : '';
    // Country and topic move into a single kicker line. They used to be five
    // coloured pills per story, which is what made the board look busy — the
    // filter row above already does the job those pills were doing.
    const kicker = [primaryCountry, humanize(primaryTopic)].filter(Boolean).join(' · ');
    return `<article class="news-card ${isLead ? 'lead' : ''}${showMedia ? '' : ' no-media'}" data-news-topics="${esc(item.topics.join('|'))}" data-news-countries="${esc(item.countries.join('|'))}">
      ${mediaHtml}
      <div class="news-kicker">${esc(kicker)}</div>
      <h3><a href="${esc(item.url)}" target="_blank" rel="noopener">${esc(headline)}</a></h3>
      ${dek ? `<p>${esc(dek)}</p>` : ''}
      <footer><span class="news-source">${esc(humanize(item.source || 'Regional source'))}</span><span class="news-stamp">${esc(item.source_tier === 1 ? "Official source" : "Regional press")} · ${esc(time)}</span></footer>
    </article>`;
  }).join('') || '<p class="muted">Regional feeds have not been refreshed yet.</p>';

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
    // Title-casing the raw key printed "Source Checked No Dated Observation" into
    // a status pill. statusChip knows the short human label for these.
    const status = statusLabels[ex.feed_status] ?? statusChip(ex.feed_status, 'Feed planned');
    const statusClass = ex.feed_status === 'proxy_watch' ? 'proxy' : 'official';
    const sectors = ((m.watch_sectors || []) as string[]).slice(0, 4).join(', ');
    const news = ((m.credible_news || []) as any[]).slice(0, 3).map((n: any) => n.name || '').join(', ');
    const links = ((m.signal_links || []) as string[]).slice(0, 4).join(', ');
    const fx = m.fx || {};
    const snap = m.market_snapshot || {};
    const barVals = ((snap.bars || []) as number[]).slice(0, 8);
    // chart_label arrives from the market snapshot as pipeline copy
    // ("Indexed activity proxy, not price history"); the disclosure below the
    // chart already says this in plain words, so don't repeat it as a heading.
    const rawChartLabel = String(snap.chart_label || '');
    const barLabel = /indexed activity|not price history|proxy/i.test(rawChartLabel)
      ? 'Market activity'
      : (rawChartLabel || 'Market activity');
    const activityChart = buildIndexedActivitySvg(barVals, barLabel);
    const barMeta = barVals.length
      ? `<span class="activity-chart-meta"><strong>Index ${Math.round(barVals[barVals.length - 1] || 0)}</strong><span>ranged ${Math.round(Math.min(...barVals))}–${Math.round(Math.max(...barVals))} this period</span></span>`
      : '';
    const observedAt = String(m.observation_at || snap.observation_at || '').slice(0, 10);
    // Read as a sentence, not a field dump — the old form printed
    // "Official source status: Official source could not be reached this cycle".
    const observationCopy = observedAt
      ? `Exchange last published ${friendlyDate(observedAt)}`
      : humanizeStatus(m.freshness_state || snap.data_status, 'No date published');
    const exchName = ex.name || 'Market source';
    const exchHtml = ex.url
      ? `<a href="${esc(ex.url)}" target="_blank" rel="noopener">${esc(exchName)}</a>`
      : esc(exchName);
    // The exchange ticker is the card's identifier; when a market has none,
    // print nothing rather than a dangling dash.
    const codeHtml = ex.code ? `<span class="market-code">${esc(ex.code)}</span>` : '<span class="market-code"></span>';
    // watch_sectors and signal_links are usually the same list — say it once.
    // snap.focus arrives as either a sentence or a list of sectors; an array
    // stringified by the template literal is what produced "a,b,c".
    const focusCopy = Array.isArray(snap.focus)
      ? snap.focus.join(', ')
      : String(snap.focus || '').replace(/,(?=\S)/g, ', ') || 'Market notices and official source updates';
    const linksHtml = links && links !== sectors
      ? `<p><strong>Linked signals:</strong> ${esc(humanize(links))}</p>`
      : '';
    marketWatchHtml += `<article class="market-card ${statusClass}">
      <div class="market-top">${codeHtml}<span class="market-status">${esc(status)}</span></div>
      <h3>${esc(humanize(m.country || 'Market'))}</h3>
      <p class="market-exchange">${exchHtml}</p>
      <p class="market-observation">${esc(observationCopy)}</p>
      <div class="market-finance-row"><span>FX ${esc(humanize(fx.pair || '—'))}</span><span>${esc(humanize(fx.rate_label || 'watch'))}</span></div>
      <p><strong>Watch:</strong> ${esc(humanize(sectors))}</p>
      <p><strong>News context:</strong> ${esc(humanize(news))}</p>
      ${linksHtml}
    </article>`;
    marketChartHtml += `<article class="market-chart-card ${statusClass}">
      <div class="market-top">${codeHtml}<span class="market-status">${esc(snap.data_status ? statusChip(snap.data_status) : status)}</span></div>
      <h3>${esc(humanize(m.country || exchName))}</h3>
      <div class="activity-chart-shell">${activityChart}</div>
      <p class="activity-readout" aria-live="polite"></p>
      <p class="activity-chart-caption"><strong>${esc(humanize(barLabel))}</strong>${barMeta}</p>
      <p class="market-chart-disclosure">Indexed activity trend, not share price.</p>
      ${snap.headline ? `<p class="market-chart-headline">${esc(humanize(snap.headline))}</p>` : ''}
      <p>${esc(humanize(focusCopy))}</p>
      <div class="market-finance-row"><span>${esc(humanize(fx.indicator || 'FX watch'))}</span><span>${esc(humanize(fx.pair || '—'))}</span></div>
    </article>`;
  }

  const regionalSources: any[] = marketSources.regional_context_sources || [];
  const regionalSourceHtml = regionalSources.slice(0, 10)
    .map((src: any) => `<span>${esc(src.name || '')}</span>`).join('');
  const marketDataSources: any[] = marketSources.market_data_sources || [];
  const fxSources: any[] = marketSources.fx_sources || [];
  // config/market_sources.json only defines `markets`, so these three arrays
  // are empty and the registry rendered as blank scaffolding. Derive it from
  // the market records the page already tracks instead of maintaining a
  // parallel list that drifts — and carry each source's fetch status, which
  // is the part with real value: which of these actually publish.
  const derivedMarketSources = marketDataSources.length ? marketDataSources : markets
    .map((m: any) => {
      const ex = m.exchange || {};
      // "Responding" means the source published a dated observation, not
      // merely that the page loaded. Jamaica and Cayman return HTTP 200 and
      // no date, which is exactly the gap worth reporting.
      const reachable = Boolean(m.observation_at);
      return ex.name || m.exchange_name
        ? {
            name: ex.name || m.exchange_name,
            code: ex.code || m.exchange_code || '',
            url: ex.url || m.source_url || '',
            reachable,
          }
        : null;
    })
    .filter(Boolean);

  const derivedFxSources = fxSources.length ? fxSources : Object.values(
    Object.fromEntries(
      markets
        .filter((m: any) => (m.fx || {}).pair)
        .map((m: any) => [m.fx.pair, { name: m.fx.pair, code: m.fx.currency || '', url: '' }]),
    ),
  );

  const derivedRegionalSources = regionalSources.length ? regionalSources : Object.values(
    Object.fromEntries(
      markets.flatMap((m: any) => (m.credible_news || []) as any[])
        .filter((n: any) => n && n.name)
        .map((n: any) => [n.name, { name: n.name, url: n.url || '' }]),
    ),
  );

  const registryGroups = [
    ['Official market data', derivedMarketSources],
    ['FX / currency', derivedFxSources],
    ['Regional context', derivedRegionalSources],
  ] as [string, any[]][];
  // Skip groups with nothing in them. config/market_sources.json currently
  // carries only `markets`, so these arrays are empty and the registry was
  // rendering three labelled rows with no sources beside them.
  for (const [label, sources] of registryGroups.filter(([, s]) => s.length)) {
    const chips = sources.map((src: any) => {
      const label = `${src.code ? esc(src.code) + ' · ' : ''}${esc(src.name || '')}`;
      const unreachable = src.reachable === false;
      const cls = unreachable ? ' class="src-unreachable"' : '';
      const title = unreachable ? ' title="Tracked, but no dated observation retrieved this cycle"' : '';
      return src.url
        ? `<a${cls}${title} href="${esc(src.url)}" target="_blank" rel="noopener">${label}</a>`
        : `<span${cls}${title}>${label}</span>`;
    }).join('');
    sourceRegistryHtml += `<div class="source-registry-group"><strong>${esc(label)}</strong><div>${chips}</div></div>`;
  }
  // An honest empty state beats "0 market data sources" over three blank
  // rows. config/market_sources.json currently defines `markets` only, so
  // the registry has nothing to list until those arrays are populated.
  const registryTotal = derivedMarketSources.length + derivedFxSources.length + derivedRegionalSources.length;
  const reachableCount = derivedMarketSources.filter((src: any) => src.reachable !== false).length;
  const sourceRegistrySummary = registryTotal
    ? `${derivedMarketSources.length} market data sources (${reachableCount} responding) · `
      + `${derivedFxSources.length} FX references · ${derivedRegionalSources.length} regional outlets`
    : 'Not populated in this cycle';
  if (!registryTotal) {
    sourceRegistryHtml = '<p class="source-registry-empty">Exchange, FX and regional-context sources are named on each market above. The consolidated registry is not populated in this cycle\'s configuration.</p>';
  }

  // ── All clusters (audit) ───────────────────────────────────
  // fallow-ignore-next-line complexity
  const allClustersHtml = clusters.map((c, i) => {
    const ct = cleanSignalTitle(c.title || '');
    const cc = c.country_cluster || '';
    const cg = cleanGrade(c.evidence_grade || '');
    const cf = c.freshness || '';
    const cd = humanize(c.decision || '').slice(0, 100);
    const ce = c.evidence || '';  // evidenceListHtml cleans and splits it
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
        ${evidenceListHtml(ce)}
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

  const nowTs = Math.floor(Date.now() / 1000);
  const theaterEvents: any[] = [];
  srcRows.slice(0, 6).forEach((src, i) => {
    theaterEvents.push({
      event: 'source_check',
      data: { ts: nowTs + i * 8, source: src.label, status: src.status },
    });
  });
  mapMarkers
    .filter((m: any) => (m.confidence || 0) >= 50)
    .slice(0, 6)
    .forEach((m: any, i: number) => {
      theaterEvents.push({
        event: 'signal_found',
        data: { ts: nowTs + 56 + i * 10, kind: m.kind, country: m.country, confidence: m.confidence, summary: m.summary },
      });
    });
  // fallow-ignore-next-line complexity
  dispatches.slice(0, 8).forEach((dispatch: any, i: number) => {
    theaterEvents.push({
      event: 'dispatch_routed',
      data: {
        ts: nowTs + 128 + i * 7,
        recipient: dispatch.persona_label || dispatch.persona_key || 'Decision-maker',
        country: canonicalCountry(dispatch.country_cluster || 'Region'),
        dispatch_id: dispatch.dispatch_id || '',
      },
    });
  });
  theaterEvents.push({
    event: 'cycle_complete',
    data: { ts: nowTs + 190, cycle: cycleId, signals: nClusters },
  });

  return {
    // Scalars
    cycleId, cycleLabel: cycleDateLabel(cycleId), nowStr, nCountries, nSources, nClusters, nPersonas, nFb, nComposite,
    // Lead signal
    lTitle, lRankingBasis, lCountry, lEvidence, lRanking, lDecision, lGrade, lRisks, leadPctStr,
    leadAction, leadWindow, leadOwner, leadDispatchId, leadDelivery, leadFeedback, leadRationale,
    // HTML fragments
    leadRoutesHtml, validationPackHtml, secSignals, receiptsHtml, boostsHtml,
    receiptsProvenanceHtml, newsHtml, newsFilterHtml,
    newsByCountryJson: JSON.stringify(newsByCountry),
    calibrationCommitmentHtml: calibrationCommitmentHtml(), marketWatchHtml, marketChartHtml, regionalSourceHtml,
    sourceRegistryHtml, sourceRegistrySummary, allClustersHtml, fbActionPills,
    srcRows,
    // Counts
    marketSourceCount: marketDataSources.length,
    fxSourceCount: fxSources.length,
    regionalNewsCount: newsItems.length,
    verdictCounts,
    // JSON blobs (embedded in <script>)
    analystData: JSON.stringify(analystData).replace(/<\//g, '<\\/'),
    mapMarkersJson: JSON.stringify(mapMarkers).replace(/<\//g, '<\\/'),
    mapDispatchesJson: JSON.stringify(mapDispatches).replace(/<\//g, '<\\/'),
    allPacksJson: JSON.stringify(allPacks).replace(/<\//g, '<\\/'),
    verdictCountsJson: JSON.stringify(verdictCounts),
    lRisksJson: JSON.stringify(lRisks),
    theaterEventsJson: JSON.stringify(theaterEvents).replace(/<\//g, '<\\/'),
    replayJsonlUrl: replayJsonlUrl.replace(/<\//g, '<\\/'),
    humanizeRulesJson,
    regionalMovementHtml, tickerHtml, frontPointersHtml,
    // Ticker items for client-side lw-rail width calculation
    tickerItemCount: tickerItems.length,
  };
}
