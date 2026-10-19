import { openCountryDrill, renderDrill } from './map.ts';

// ── Reader preferences ────────────────────────────────────────────────────
// Persona and followed markets, kept in localStorage. The desk already routes
// one signal to several personas; this lets the reader claim one and have the
// page lead with their lane instead of broadcasting the same order to everyone.
const PREFS_KEY = 'future-caribbean:prefs';
export const prefs: { lens: string; follows: string[] } = (() => {
  try {
    const raw = JSON.parse(localStorage.getItem(PREFS_KEY) || '{}');
    return { lens: raw.lens || '', follows: Array.isArray(raw.follows) ? raw.follows : [] };
  } catch { return { lens: '', follows: [] }; }
})();
function savePrefs() {
  try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch {}
}
export function isFollowed(country: string): boolean { return prefs.follows.includes(country); }
export function toggleFollow(country: string): void {
  const i = prefs.follows.indexOf(country);
  if (i >= 0) prefs.follows.splice(i, 1); else prefs.follows.push(country);
  savePrefs();
  paintFollows();
  renderDrill();
}

function countForLens(lens) {
  if (!lens) return 0;
  return Object.values(MAP_DISPATCHES).flat()
    .filter(d => (d.persona_label || '') === lens).length;
}

export function paintLens(): void {
  const select = document.getElementById('lens-select');
  const hint = document.getElementById('lens-hint');
  if (select) select.value = prefs.lens;
  if (hint) {
    const n = countForLens(prefs.lens);
    hint.textContent = prefs.lens
      ? `${n} briefing${n === 1 ? '' : 's'} routed to you this cycle`
      : 'Pick a lens and the desk leads with your briefings';
  }
}

export function paintFollows(): void {
  const wrap = document.getElementById('follow-chips');
  if (!wrap) return;
  if (!prefs.follows.length) {
    wrap.innerHTML = '<span class="deskbar-none">Select a country on the map, then Follow.</span>';
    return;
  }
  wrap.textContent = '';
  for (const country of prefs.follows) {
    const stories = (typeof NEWS_BY_COUNTRY !== 'undefined' && NEWS_BY_COUNTRY[country] || []).length;
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'follow-chip';
    chip.title = `Open ${country}`;
    const name = document.createElement('b');
    name.textContent = country;
    chip.appendChild(name);
    if (stories) {
      const count = document.createElement('i');
      count.textContent = String(stories);
      chip.appendChild(count);
    }
    chip.addEventListener('click', () => {
      openCountryDrill(country);
      document.getElementById('map-drill')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
    wrap.appendChild(chip);
  }
}

export function initLensSelect(): void {
  document.getElementById('lens-select')?.addEventListener('change', event => {
    prefs.lens = event.target.value;
    savePrefs();
    paintLens();
    renderDrill();
  });
}
