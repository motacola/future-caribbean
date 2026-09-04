// Port of humanizer.py — natural-language rewrite rules for pipeline artifacts.
// JS regex syntax: $1 backreferences (Python uses \1; the JSON export already
// converts them so the client-side twin receives the same array).

const HUMANIZE_RULES: [string, string][] = [
  ["^([^:]+): \\+?([\\d.]+)% multi-source capital surge — market entry window open$",
   "Money is moving into $1: up $2%, and more than one source says so"],
  ["^([^:]+): \\+?([\\d.]+)% multi-source investment validated — opportunity active$",
   "Money is moving into $1: up $2%, validated by several sources"],
  ["^([^:]+): \\+?([\\d.]+)% capital surge on a single official source — market entry window open$",
   "Money is moving into $1: up $2%, on one official source so far"],
  ["^([^:]+): \\+?([\\d.]+)% investment movement, one source — needs corroboration$",
   "Money is moving into $1: up $2%, but only one source says so yet"],
  ["^([^:]+): FDI trending at \\+?([\\d.]+)% — screening trigger active$",
   "Foreign investment into $1 is up $2%. Worth a first look"],
  ["^([^:]+): (\\d+) active procurements? — bidding window open$",
   "$2 live tenders in $1. Bids are open now"],
  ["^([^:]+): food supply indicators shifting — supply chain implications$",
   "Food supply numbers are shifting in $1. Keep an eye on the supply chain"],
  ["^Capital convergence: (\\d+) Caribbean economies showing multi-source investment momentum$",
   "$1 Caribbean economies are pulling in money at the same time"],
  ["^([^:]+): GDP growth signals expanding tourist economy$",
   "$1's economy is growing, which is good news for tourism demand"],
  ["^([^:]+): economic stress indicators rising.*$",
   "Stress numbers are rising in $1. Worth watching"],
  ["Investigate (.+?) as a capital deployment target this cycle\\. Multi-source validation \\((.+?)\\) confirms directional signal — next step is operator discovery and market entry assessment\\.",
   "Take a serious look at $1 this cycle. Several sources point the same way ($2), so the next step is finding local partners and checking for a real way in."],
  ["Assess competitive positioning in (.+?)\\. FDI movement \\((.+?)\\) signals growing market or incoming competition — evaluate (.+?)\\.",
   "If you operate in $1, take stock. New money ($2) means a growing market, or new competition arriving."],
  ["Assess portfolio exposure in (.+?)\\. Economic stress indicators \\((.+?)\\) may affect existing positions or timing\\.",
   "Holding positions in $1? Stress numbers are at $2. Check your exposure and your timing."],
  ["Assess (.+?) demand trajectory\\. (.+?) change — adjust capacity plans\\.",
   "Demand in $1 looks to be shifting ($2), so it is worth revisiting capacity plans."],
  ["Screen (.+?) for investment readiness\\. FDI movement \\((.+?)\\) is a screening trigger — cross-reference with sector conditions before deploying capital\\.",
   "$1 is worth a first screen: money is moving ($2). Check the sector picture before committing anything."],
  ["Multi-source validation reduces screening risk — capital follows verified signals",
   "When several sources agree, half the homework is already done"],
  ["FDI movement in your operating country signals competition or demand growth — assess positioning",
   "Money moving into your market means demand, or competition. Either way, better to know early"],
  ["Active procurement directly maps to operational capacity needs — first to respond wins",
   "Live tenders reward whoever responds first"],
  ["Cross-country investment velocity signals where to focus ecosystem support and founder matching",
   "Where the money lands is where founders will need support next"],
  ["Economic stress indicators drive policy response and media narratives",
   "Stress numbers move policy, and headlines"],
  ["Food trade data reveals supply chain gaps that local founders and agri-tech can fill",
   "Gaps in the food trade are openings for local founders"],
  ["GDP growth in tourism-relevant economies signals demand trajectory — plan capacity accordingly",
   "A growing economy means more visitors. Plan capacity for it"],
  ["CDB/IDB project pipeline is the primary lead source for project-based business development",
   "The CDB and IDB project pipeline is where project work starts"],
  ["Food security is a regional stability indicator — tracks pressure points before they become crises",
   "Food security numbers flag pressure early, before it becomes a crisis"],
  ["Which verified opportunity to investigate for capital deployment or partnership entry",
   "Which opportunity deserves your attention first"],
  ["Analyst prior from widely reported sector drivers — requires local confirmation",
   "Widely reported driver, still needs confirming on the ground"],
  ["(\\d+) independent evidence categories already attached",
   "evidence already attached from $1 directions"],
  ["High-confidence signal", "Strong signal"],
  ["Worth one validation conversation this cycle\\.", "Worth one real conversation this cycle."],
  ["Umbrella private-sector body — operator discovery",
   "Knows the private sector. Ask who's really operating"],
  ["National chamber — operator discovery",
   "The national chamber, a shortcut to who's doing business"],
  ["World Bank FDI movement data shows:\\s*(.+)", "World Bank sees foreign investment moving into $1"],
  ["WB FDI surge detected:\\s*", "World Bank sees money moving into "],
  ["\\bWB\\b", "World Bank"],
  ["\\bFDI\\b", "foreign investment"],
  // ── 2026-08-22 voice pass — mirrors the rules added to humanizer.py ──
  ["^Insurance capital deployment for reconstruction / parametric trigger validation$",
   "Insurance money is moving for rebuilding. Check what the payout trigger covers"],
  ["^Private sector credit expansion = banking confidence = investment timing signal$",
   "Banks are lending more, usually a good moment to time an investment"],
  ["^Deposit base expansion = currency union stability = confidence signal$",
   "Deposits are growing across the currency union, a quiet sign of confidence"],
  ["^Which country-sector pair to validate for investment readiness$",
   "Pick the country and sector most ready for investment, and check it holds up"],
  ["Calibrated confidence (\\d+)/100 with (\\d+) evidence categories including dated procurement or corroborated sector news\\. Worth one validation conversation\\.",
   "Confidence sits at $1 out of 100, backed by $2 kinds of evidence including a dated tender or corroborated news. Worth one real conversation."],
  ["Calibrated confidence (\\d+)/100 with (\\d+) evidence categories, but no dated country tender or corroborated sector article yet — advance after confirmation\\.",
   "Confidence sits at $1 out of 100 with $2 kinds of evidence, but nothing dated or independently corroborated yet. Hold until that lands."],
  ["Calibrated confidence (\\d+)/100 with (\\d+) evidence categories\\. Keep on the desk; advance only after the unresolved questions below are answered\\.",
   "Confidence sits at $1 out of 100 with $2 kinds of evidence. Keep it on the desk until the open questions below get answers."],
  ["Calibrated confidence (\\d+)/100 with no corroborating evidence categories\\. Park unless new corroborating data arrives next cycle\\.",
   "Confidence sits at just $1 out of 100 with nothing to back it yet. Park it unless fresh evidence arrives next cycle."],
  ["Investigate (.+?) as a capital deployment target this cycle\\. One official source shows the movement \\((.+?)\\) — corroborate it before acting, then move to operator discovery\\.",
   "Take a serious look at $1 this cycle. One official source shows the move ($2). Get a second one before you act, then start finding local partners."],
  ["Which specific sectors are driving the movement in (.+?)\\? No official sector-breakdown dataset matched this cycle\\.",
   "Which industries are actually driving this in $1? Nobody has published a breakdown yet."],
  ["Validate fit with registry-listed operators \\((.+?)\\) before outreach\\.",
   "Check these companies are the right fit before you reach out: $1."],
  ["^Analyst prior — sector likely but unconfirmed$",
   "Likely, but nobody has confirmed it yet"],
  ["\\bcorroborated\\b",
   "confirmed"],
  ["\\bCorroborated\\b",
   "Confirmed"],
  ["\\bunconfirmed\\b",
   "not yet confirmed"],
  ["\\bUnconfirmed\\b",
   "Not yet confirmed"],
  ["\\bcorroboration\\b",
   "a second source"],
  ["\\boperator discovery\\b",
   "finding local partners"],
  ["^Source registry now tracked by the desk$",
   "Where the desk gets this"],
  ["Review (.+?): signal detected\\. Validate locally before action\\.",
   "The desk logged movement in $1 but nothing specific yet. Worth a local check before it firms up."],
  ["Signal context for (.+?): signal detected\\. Use this dispatch as a briefing input or narrative lead\\.",
   "Movement logged in $1, with no detail attached yet: background for a briefing rather than a story on its own."],
  ["^(.+?): signal detected$",
   "Early signal in $1, no detail yet"],
  ["\\(signal detected\\)",
   "(no figure attached yet)"],
];

const _compiled: [RegExp, string][] = HUMANIZE_RULES.map(([p, r]) => {
  try { return [new RegExp(p), r]; } catch { return null; }
}).filter(Boolean) as [RegExp, string][];

export function humanize(text: string | null | undefined): string {
  if (!text) return text ?? '';
  let out = String(text);
  for (const [rx, r] of _compiled) {
    out = out.replace(rx, r);
  }
  return out;
}

// JSON for the client-side JS twin embedded in the page script.
export const humanizeRulesJson = JSON.stringify(HUMANIZE_RULES).replace(/<\//g, '<\\/');

// ── Feed hygiene ────────────────────────────────────────────
// Syndicated feeds hand us headlines and summaries that were written for a
// CMS, not for a reader: SHOUTED procurement notices, editor usernames,
// publish timestamps, tracking tokens, and summaries that are just the
// headline again. The rules above rewrite *our* phrasing; these clean up
// text we did not write before it reaches the page.

// A token stays capitalised through de-shouting if it is parenthesised
// (almost always an acronym in a tender notice), carries a digit, or is a
// roman numeral — "(MTDSIP)", "2027-2031", "II".
const SHOUT_KEEP = /^[([]|\d|^[IVXLC]+[.,)]?$/;

/** Collapse whitespace and drop zero-width junk. */
function tidy(text: string): string {
  return String(text).replace(/[\u200B-\u200F\uFEFF]/g, '').replace(/\s+/g, ' ').trim();
}

/** Strip punctuation and case so two strings can be compared for sameness. */
function comparable(text: string): string {
  return tidy(text).toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
}

/** A word that is shouting: two or more letters, all of them capitals. */
function isShouting(word: string): boolean {
  const letters = word.replace(/[^A-Za-z]/g, '');
  return letters.length >= 2 && letters === letters.toUpperCase();
}

/**
 * Sentence-case runs of three or more consecutive ALL-CAPS words, so
 * "FORMULATION OF A MEDIUM-TERM DEVELOPMENT STRATEGY" and an inline
 * "INVITATION TO BID – WORKS" both read as prose. Isolated capitals are
 * left alone — those are acronyms (CDB, IDB, U.S.), not shouting.
 */
function unshout(text: string): string {
  const words = text.split(' ');
  const out = [...words];
  let runStart = -1;
  let runShouts = 0;

  const flush = (end: number) => {
    if (runStart >= 0 && runShouts >= 3) {
      let first = -1;
      for (let i = runStart; i < end; i++) {
        if (SHOUT_KEEP.test(words[i])) continue;
        out[i] = words[i].toLowerCase();
        if (first < 0) first = i;
      }
      // Open the sentence on the first word we actually lowered — the run may
      // start on a preserved acronym.
      if (first >= 0) out[first] = out[first].charAt(0).toUpperCase() + out[first].slice(1);
    }
    runStart = -1;
    runShouts = 0;
  };

  for (let i = 0; i < words.length; i++) {
    const letters = words[i].replace(/[^A-Za-z]/g, '');
    if (isShouting(words[i])) {
      if (runStart < 0) runStart = i;
      runShouts++;
    } else if (letters.length > 1 || /[a-z]/.test(letters)) {
      flush(i);
    }
    // Neutral tokens — "–", "2027-2031", a lone "A" — neither start nor
    // break a run.
  }
  flush(words.length);
  return out.join(' ');
}

/**
 * Clean a syndicated headline: drop tracking tokens like "(fXoWngxfom)" —
 * mixed-case runs of 8+ characters, which no real acronym looks like — and
 * de-shout notices that arrive in full caps.
 */
function stripTrackingTokens(text: string): string {
  return text.replace(/\s*\(([A-Za-z0-9]{8,})\)/g, (whole, token: string) =>
    /[a-z]/.test(token) && /[A-Z]/.test(token) ? '' : whole);
}

export function cleanHeadline(title: string | null | undefined): string {
  if (!title) return '';
  return humanize(tidy(unshout(stripTrackingTokens(tidy(title)))));
}

// Editor usernames ("sonia.harrison..."), CMS publish stamps
// ("Tue, 08/11/2026 - 17:29") and bare boilerplate that adds nothing.
const DEK_NOISE: RegExp[] = [
  /\b[a-z][a-z0-9_-]*\.[a-z][a-z0-9_-]*\s*(?:\.{2,}|…)/g,
  // A truncated CMS author email at the head of the summary — the CDB feed
  // opens one notice with "alice.castro@c… (This is a republication…".
  /^[a-z][a-z0-9._-]*@[a-z0-9.-]*\s*(?:\.{2,}|…)?\s*/i,
  // "Lothar Mikulla Summary The booklet…" — a byline the feed prepends before
  // the real sentence. Two or three capitalised names, then Summary/Abstract.
  /^(?:[A-Z][a-z]+\s+){1,3}(?=(?:Summary|Overview|Abstract)\s+[A-Z])/,
  /\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s*\d{1,2}\/\d{1,2}\/\d{2,4}\s*-\s*\d{1,2}:\d{2}\s*/g,
  /\b\d{1,2}\/\d{1,2}\/\d{4}\s*-\s*\d{1,2}:\d{2}\s*/g,
  /\bRead more\b\.?/gi,
];

// A CMS author slug left at the head of the summary — "insom_admn_cdb",
// "sonia.harrison" — recognised by its separators and the capitalised word
// that starts the real sentence after it.
const LEADING_SLUG = /^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+\s+(?=[A-Z])/;

/** Cut to `limit` characters on a word boundary, with a real ellipsis. */
function truncateWords(text: string, limit: number): string {
  if (text.length <= limit) return text;
  const cut = text.slice(0, limit);
  const lastSpace = cut.lastIndexOf(' ');
  return `${(lastSpace > limit * 0.6 ? cut.slice(0, lastSpace) : cut).replace(/[\s,;:.–—-]+$/, '')}…`;
}

/**
 * Clean a syndicated summary for use as a dek. Returns '' when the summary
 * only restates the headline — an empty dek reads better than the same
 * sentence printed twice.
 */
export function cleanDek(summary: string | null | undefined, title?: string | null, limit = 190): string {
  if (!summary) return '';
  let out = tidy(summary);
  for (const rule of DEK_NOISE) out = out.replace(rule, ' ');
  out = unshout(tidy(stripTrackingTokens(out)));

  // Feeds open with a section word before repeating the headline ("Overview
   // Future Leaders Network The Caribbean Development Bank's Future Leaders
   // Network…"). Strip it first, or the headline-prefix test below never
   // matches and the title is printed twice in a row.
  out = tidy(out.replace(/^(?:Summary|Overview|Abstract|Background)\s+(?=[A-Z])/, ''));

  if (title) {
    const headline = comparable(title);
    // Feeds commonly prefix the summary with the headline; drop that prefix.
    // Matched word-by-word with loose separators, because the summary's
    // punctuation rarely matches the headline's character for character.
    if (headline && comparable(out).startsWith(headline)) {
      const pattern = headline.split(' ').map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('[^A-Za-z0-9]+');
      out = tidy(out.replace(new RegExp(`^[^A-Za-z0-9]*${pattern}[^A-Za-z0-9]*`, 'i'), ''));
      out = tidy(out.replace(LEADING_SLUG, '').replace(/^(?:Summary|Overview|Abstract)\s+(?=[A-Z])/, ''));
      // CDB tender feeds bury their own kicker behind the headline, a byline and
      // a timestamp: "…(BESRPII) sonia.harrison… Tue, 08/11/2026 - 17:29
      // INVITATION TO BID – WORKS The Government of Belize…". Only now, with the
      // headline gone and unshout having folded the caps, is it at the front.
      // The headline already says what kind of notice this is.
      // No /i here: it would make [a-z] and the (?=[A-Z]) lookahead both
      // case-blind, so the match ended immediately and left "works" behind.
      // unshout has already normalised the caps by this point.
      out = tidy(out.replace(/^Invitation to (?:bid|tender)\s*[–-]?\s*[a-z ]{0,24}?(?=[A-Z])/, ''));
    }
    const body = comparable(out);
    // Whatever is left is only useful if it says something new. A long dek
    // that happens to name the project again is fine — only drop it when it
    // is the headline, sits inside the headline, or barely exceeds it.
    if (!body || body.length < 40) return '';
    if (headline.includes(body)) return '';
    if (body.includes(headline) && body.length < headline.length * 1.35) return '';
  }

  return truncateWords(humanize(out), limit);
}

// Machine status identifiers that were being printed to the page verbatim.
const STATUS_COPY: Record<string, string> = {
  source_checked_no_dated_observation: 'Source checked, no dated close published',
  no_dated_observation: 'No dated close published',
  official_source_identified: 'Official source identified',
  proxy_watch: 'Proxy watch',
  fallback_cached: 'Cached fallback',
  stale_fallback: 'Last published close, now some weeks old',
  unavailable: 'Official source could not be reached this cycle',
  date_unavailable: 'Date unavailable',
  current: 'Current',
  delayed: 'Delayed',
  stale: 'Stale',
  live: 'Live feed',
  planned: 'Feed planned',
};

// Chips sit beside one-word labels like "Current" in a 9px uppercase pill, so
// they need a label, not a sentence. The descriptive line under the card still
// gets the full STATUS_COPY phrasing.
const STATUS_CHIP: Record<string, string> = {
  source_checked_no_dated_observation: 'Awaiting close',
  no_dated_observation: 'Awaiting close',
  official_source_identified: 'Source identified',
  fallback_cached: 'Cached',
  stale_fallback: 'Older close',
  unavailable: 'Source unreachable',
  date_unavailable: 'No date',
  proxy_watch: 'Proxy',
};

/** Short label for a status pill. Falls back to the readable sentence form. */
export function statusChip(raw: string | null | undefined, fallback = 'Status unknown'): string {
  const key = tidy(raw ?? '').toLowerCase().replace(/[\s-]+/g, '_');
  if (!key) return fallback;
  return STATUS_CHIP[key] ?? humanizeStatus(raw, fallback);
}

/** Render a pipeline status identifier as something a reader can parse. */
export function humanizeStatus(raw: string | null | undefined, fallback = 'Status unknown'): string {
  const key = tidy(raw ?? '').toLowerCase().replace(/[\s-]+/g, '_');
  if (!key) return fallback;
  if (STATUS_COPY[key]) return STATUS_COPY[key];
  const words = key.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}
