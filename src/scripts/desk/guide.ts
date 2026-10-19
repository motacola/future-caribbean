import { revealTarget } from './nav.ts';
import { showCountryInNewsDesk } from './news.ts';
import { isFollowed, toggleFollow } from './prefs.ts';
import { openCountryDrill } from './map.ts';

// ── Desk guide ────────────────────────────────────────────────────────────
// A navigator first, a Q&A second. Navigation intents resolve here and act on
// the page immediately; anything else goes to /api/ask, the same deterministic
// endpoint the inline "Ask the desk" panel uses. No model runs in the browser.
const GUIDE_PLACES = [
  { id: 'regional-news',      label: 'Regional news desk', terms: ['news', 'headlines', 'stories', 'press', 'wire'] },
  { id: 'decision-workspace', label: "Today's call",       terms: ["today's call", 'todays call', 'the call', 'briefing', 'lead call', 'decision'] },
  { id: 'market-watch',       label: 'Market watch',       terms: ['market', 'markets', 'exchange', 'stocks', 'chart', 'fx'] },
  { id: 'receipts',           label: "The desk's receipts", terms: ['receipts', 'track record', 'accuracy', 'past calls', 'history'] },
  { id: 'map-hero',           label: 'The map',            terms: ['map', 'top', 'start', 'home', 'front page'] },
  { id: 'theater',            label: 'Watch the desk work', terms: ['theater', 'watch the desk', 'live feed', 'stream'] },
  { id: 'about-abeng',       label: 'What is Abeng', terms: ['what is this', 'about', 'how it works', 'explain the site'] },
  { id: 'for-agents',         label: 'Machine-readable edition', terms: ['api', 'agent', 'machine readable', 'json', 'mcp', 'developer'] },
];

const guideEls: Record<string, any> = {};
let guideBusy = false;

function guideKnownCountries() {
  const fromMap = (typeof MAP_MARKERS !== 'undefined' ? MAP_MARKERS : []).map(m => m.country);
  const fromNews = typeof NEWS_BY_COUNTRY !== 'undefined' ? Object.keys(NEWS_BY_COUNTRY) : [];
  return [...new Set([...fromMap, ...fromNews])].filter(Boolean);
}

function guideMatchCountry(text) {
  const q = text.toLowerCase();
  // Longest name first so "St Kitts & Nevis" is not shadowed by a shorter match.
  return guideKnownCountries()
    .sort((a, b) => b.length - a.length)
    .find(c => q.includes(c.toLowerCase())) || '';
}

function guideSay(role: string, text: string, actions?: { label: string; run: () => void }[]) {
  const thread = guideEls.thread;
  if (!thread) return;
  const msg = document.createElement('div');
  msg.className = `guide-msg ${role}`;
  msg.textContent = text;
  if (actions && actions.length) {
    const row = document.createElement('div');
    row.className = 'guide-act';
    for (const action of actions) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = action.label;
      button.addEventListener('click', action.run);
      row.appendChild(button);
    }
    msg.appendChild(row);
  }
  thread.appendChild(msg);
  thread.scrollTop = thread.scrollHeight;
}

function guideGoto(id, label) {
  const target = revealTarget(id);
  if (!target) return false;
  target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  guideSay('desk', `Taking you to ${label}.`);
  return true;
}

function guideOpenCountry(country) {
  openCountryDrill(country);
  document.getElementById('map-drill')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  const stories = (typeof NEWS_BY_COUNTRY !== 'undefined' && NEWS_BY_COUNTRY[country] || []).length;
  const briefings = (typeof MAP_DISPATCHES !== 'undefined' && MAP_DISPATCHES[country] || []).length;
  const parts = [];
  if (briefings) parts.push(`${briefings} briefing${briefings === 1 ? '' : 's'}`);
  if (stories) parts.push(`${stories} ${stories === 1 ? 'story' : 'stories'}`);
  guideSay('desk', `${country} is open on the map — ${parts.length ? parts.join(' and ') + ' this cycle.' : 'watchlist only this cycle.'}`,
    [
      stories ? { label: `${country} news`, run: () => showCountryInNewsDesk(country) } : null,
      { label: isFollowed(country) ? `Unfollow ${country}` : `Follow ${country}`, run: () => { toggleFollow(country); guideSay('desk', isFollowed(country) ? `Following ${country}.` : `No longer following ${country}.`); } },
    ].filter(Boolean));
}

async function guideAskApi(question) {
  guideBusy = true;
  if (guideEls.send) guideEls.send.disabled = true;
  guideSay('desk', 'Checking this cycle’s files…');
  const pending = guideEls.thread?.lastElementChild;
  try {
    const res = await fetch('/api/ask', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    pending?.remove();
    guideSay('desk', humanizeJs(data.answer) || 'No answer came back for that.');
  } catch {
    pending?.remove();
    guideSay('desk', 'The desk API is not reachable from this copy of the page. Navigation still works — try "show me Guyana" or "take me to market watch".');
  }
  guideBusy = false;
  if (guideEls.send) guideEls.send.disabled = false;
}

function guideHandle(rawInput) {
  const input = (rawInput || '').trim();
  if (!input || guideBusy) return;
  guideSay('you', input);
  const q = input.toLowerCase();

  if (/^(help|what can you do|options)\b/.test(q)) {
    guideSay('desk', 'I can move you around the page and answer questions about this cycle.\nTry: "show me Guyana", "news about Jamaica", "take me to market watch", "follow Belize", "read as investor", or "explain the lead".');
    return;
  }

  const country = guideMatchCountry(q);

  // "news about X" is a different destination from "show me X".
  if (country && /\b(news|headlines|stories|press)\b/.test(q)) {
    showCountryInNewsDesk(country);
    guideSay('desk', `Filtered the news desk to ${country}.`);
    return;
  }
  if (country && /\b(follow|watch|track)\b/.test(q)) {
    if (!isFollowed(country)) toggleFollow(country);
    guideSay('desk', `Following ${country}. It is in your desk bar now.`);
    return;
  }
  if (/\bread(ing)? as\b|\blens\b|\bpersona\b/.test(q)) {
    const select = document.getElementById('lens-select');
    // Match on any distinctive word of the option, so "read as investor" finds
    // "Diaspora Investor" and "operator" finds "Regional Founder/Operator".
    const option = [...(select?.options || [])]
      .filter(o => o.value)
      .map(o => ({
        o,
        hits: o.value.toLowerCase().split(/[^a-z]+/).filter(w => w.length > 3 && q.includes(w)).length,
      }))
      .filter(x => x.hits > 0)
      .sort((a, b) => b.hits - a.hits)[0]?.o;
    if (select && option) {
      select.value = option.value;
      select.dispatchEvent(new Event('change'));
      document.getElementById('deskbar')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      guideSay('desk', `Reading as ${option.value}. Briefings routed to you now lead the map drill.`);
      return;
    }
    guideSay('desk', 'Pick a lens in the desk bar: Diaspora Investor, Ecosystem Builder, Founder / Operator, Procurement Watcher, Policy / Media, or Operations / Resilience.',
      [{ label: 'Open desk bar', run: () => document.getElementById('deskbar')?.scrollIntoView({ behavior: 'smooth', block: 'center' }) }]);
    return;
  }
  // A bare country name, or "show me X", is a map drill.
  if (country && (/\b(show|open|go to|take me|drill|look at)\b/.test(q) || q.split(/\s+/).length <= 3)) {
    guideOpenCountry(country);
    return;
  }
  const place = GUIDE_PLACES.find(p => p.terms.some(t => q.includes(t)));
  if (place && /\b(show|open|go|take me|jump|scroll|where)\b/.test(q)) {
    if (guideGoto(place.id, place.label)) return;
  }
  if (country) { guideOpenCountry(country); return; }
  if (place && guideGoto(place.id, place.label)) return;

  guideAskApi(input);
}

function setupGuide() {
  guideEls.fab = document.getElementById('guide-fab');
  guideEls.panel = document.getElementById('guide-panel');
  guideEls.thread = document.getElementById('guide-thread');
  guideEls.form = document.getElementById('guide-form');
  guideEls.input = document.getElementById('guide-input');
  guideEls.send = document.getElementById('guide-send');
  guideEls.chips = document.getElementById('guide-chips');
  if (!guideEls.fab || !guideEls.panel) return;

  const open = () => {
    guideEls.panel.hidden = false;
    guideEls.fab.setAttribute('aria-expanded', 'true');
    guideEls.input?.focus();
    if (!guideEls.thread.childElementCount) {
      guideSay('desk', 'Ask me about this cycle, or tell me where to go. Say "help" for what I can do.');
    }
  };
  const close = () => {
    guideEls.panel.hidden = true;
    guideEls.fab.setAttribute('aria-expanded', 'false');
    guideEls.fab.focus();
  };

  guideEls.fab.addEventListener('click', open);
  document.getElementById('guide-close')?.addEventListener('click', close);
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !guideEls.panel.hidden) close();
  });
  guideEls.form?.addEventListener('submit', e => {
    e.preventDefault();
    const value = guideEls.input.value;
    guideEls.input.value = '';
    guideHandle(value);
  });

  for (const chip of ['Show me Guyana', 'Take me to market watch', 'Explain the lead', 'What changed this cycle?']) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = chip;
    button.addEventListener('click', () => guideHandle(chip));
    guideEls.chips?.appendChild(button);
  }
}

export function initGuide(): void {
  // The guide markup sits at the end of the document, below this script, so wait
  // for the parser before wiring it up.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupGuide);
  } else {
    setupGuide();
  }
}
