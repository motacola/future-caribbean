// The map hero: Leaflet markers, the country drill (React via CDN + htm), and
// the expanded-map overlay.
import { escapeMapText } from './util.ts';
import { prefs, isFollowed, toggleFollow } from './prefs.ts';
import { showCountryInNewsDesk } from './news.ts';

let drillReact: { render: (country: string | null) => void } | null = null;

function createDrillReact() {
  if (typeof React === 'undefined' || typeof ReactDOM === 'undefined' || typeof htm === 'undefined') return null;
  const html = htm.bind(React.createElement);

  function safeExternalUrl(value) {
    try {
      const url = new URL(String(value || ''), window.location.origin);
      return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
    } catch {
      return '';
    }
  }

  function FollowButton({ country }) {
    const on = typeof isFollowed === 'function' && isFollowed(country);
    return html`
      <button
        type="button"
        class=${`drill-follow${on ? ' on' : ''}`}
        aria-pressed=${on ? 'true' : 'false'}
        onClick=${() => toggleFollow(country)}>
        ${on ? '\u2713 Following' : 'Follow'}
      </button>`;
  }

  // The drill used to show three bare links from the marker payload. It now
  // serves the news desk's own stories for the country, so tapping the map is a
  // way to read a country — news beside data — not just a signal readout.
  function CountryNews({ country, marker }) {
    const desk = (typeof NEWS_BY_COUNTRY !== 'undefined' && NEWS_BY_COUNTRY[country]) || [];
    const fallback = (marker.news || []).map(item => ({
      title: item.title, url: item.url, source: item.source, age: '', topic: '', tier: '',
    }));
    const stories = (desk.length ? desk : fallback)
      .map((item, index) => ({ ...item, href: safeExternalUrl(item.url), key: item.url || `${item.title}-${index}` }))
      .filter(item => item.href);

    if (!stories.length) {
      return html`
        <div class="drill-news">
          <div class="drill-news-head"><strong>In the news</strong></div>
          <p class="drill-news-empty">No ${country} coverage in this cycle. The desk keeps watching.</p>
        </div>`;
    }
    return html`
      <div class="drill-news">
        <div class="drill-news-head">
          <strong>In the news</strong>
          <span>${stories.length} ${stories.length === 1 ? 'story' : 'stories'}</span>
        </div>
        <ul class="drill-news-list">
          ${stories.slice(0, 5).map(item => html`
            <li key=${item.key}>
              <a href=${item.href} target="_blank" rel="noopener noreferrer">${item.title || 'Open coverage'}</a>
              <span>${[item.source, item.age].filter(Boolean).join(' · ')}</span>
            </li>`)}
        </ul>
        ${desk.length > 5
          ? html`<button type="button" class="drill-news-more" onClick=${() => showCountryInNewsDesk(country)}>
              All ${desk.length} ${country} stories →
            </button>`
          : null}
      </div>`;
  }

  function LifecyclePanel({ marker }) {
    const evidence = marker.evidence_mix || { wb: 0, idb: 0, noaa: 0, ndbc: 0, caricom: 0, cdb: 0 };
    const sourceKeys = ['wb', 'idb', 'noaa', 'ndbc', 'caricom', 'cdb'];
    const sourceLabels = { wb: 'World Bank', idb: 'IDB', noaa: 'NOAA', ndbc: 'NDBC', caricom: 'CARICOM', cdb: 'CDB' };
    const sourceColors = { wb: 'sea', idb: 'reef', noaa: 'storm', ndbc: 'sun', caricom: 'sand', cdb: 'reef' };
    const evidenceTotal = sourceKeys.reduce((sum, key) => sum + (Number(evidence[key]) || 0), 0);
    const evidencePct = key => evidenceTotal > 0
      ? Math.round(100 * (Number(evidence[key]) || 0) / evidenceTotal)
      : 0;
    const lifecycle = marker.lifecycle || { last_seen: 'unknown', cadence: 'Cadence not supplied', scope: 'Source status', freshness: 'stale' };
    const freshnessClass = marker.freshness_state === 'current'
      ? 'fresh'
      : marker.freshness_state === 'delayed'
        ? 'aging'
        : 'stale';
    return html`
      <div class="drill-lifecycle" data-freshness=${freshnessClass}>
        <div class="drill-lifecycle-head">
          <span class="drill-lifecycle-label">${lifecycle.scope || 'Source status'}</span>
          <span class="drill-lifecycle-state drill-lifecycle-state--${freshnessClass}">${lifecycle.freshness || freshnessClass}</span>
        </div>
        <div class="drill-lifecycle-fields">
          <span class="drill-lifecycle-key">${lifecycle.time_label || 'Observed'}</span>
          <span class="drill-lifecycle-val">${lifecycle.last_seen || 'unknown'}</span>
          <span class="drill-lifecycle-key">Update cadence</span>
          <span class="drill-lifecycle-val">${lifecycle.cadence || 'Scheduled every 4h'}</span>
        </div>
        <div class="drill-evidence">
          <span class="drill-lifecycle-key">
            ${evidenceTotal > 0
              ? `Confirmed source groups (${evidenceTotal})`
              : 'No corroborating signal sources yet'}
          </span>
          ${evidenceTotal > 0
            ? html`
                <div class="drill-evidence-bar" role="img" aria-label=${`${evidenceTotal} confirmed source group${evidenceTotal === 1 ? '' : 's'}`}>
                  ${sourceKeys.filter(key => Number(evidence[key]) > 0).map(key => html`
                    <span
                      key=${key}
                      class="drill-evidence-seg"
                      data-key=${key}
                      style=${{ width: evidencePct(key) + '%', background: `var(--caribbean-${sourceColors[key]})` }}
                      title=${`${sourceLabels[key]}: ${evidence[key] || 0}`}
                    ></span>`)}
                </div>`
            : html`<p class="drill-evidence-empty">Watchlist context only; no source family is being claimed as corroboration.</p>`}
        </div>
      </div>`;
  }

  function DrillPanel({ country }) {
    if (!country) return html`<p class="map-drill-empty">Select a country to see what the desk found.</p>`;
    const items = MAP_DISPATCHES[country] || [];
    const marker = MAP_MARKER_BY_COUNTRY[country] || {};
    const fx = marker.fx || {};
    const market = marker.market || {};
    const snapshot = market.snapshot || {};
    const marketLabel = market.code ? `${market.code} · ${snapshot.headline || market.name || 'Market watch'}` : 'No domestic exchange / watchlist';
    if (!items.length) {
      return html`
        <div class="rise-in">
          <div class="map-drill-head"><strong>${country}</strong><${FollowButton} country=${country} /></div>
          <div class="map-market-panel">
            <div><span>FX indicator</span><strong>${fx.pair || '—'}</strong><p>${fx.rate_label || 'Watch'} · ${fx.indicator || 'FX watch'}</p></div>
            <div><span>Market layer</span><strong>${marketLabel}</strong><p>${snapshot.data_status || market.status || 'source watch'} </p></div>
            <div><span>Finance signal</span><strong>${snapshot.focus || fx.signal || 'Signals, official notices, and local context'}</strong><p>${marker.finance_signal || marker.ranking_rationale || 'Ranking appears when a live signal is active.'}</p></div>
          </div>
          <${LifecyclePanel} marker=${marker} />
          <${CountryNews} country=${country} marker=${marker} />
          <div class="map-drill-grid">
            <article>
              <span>WATCHLIST · ${marker.confidence || 0}/100</span>
              <h3>${marker.summary || 'Regional market watch'}</h3>
              <p>${marker.ranking_rationale || 'Nothing confirmed yet. We watch official notices, currency pressure, and market sources on this island, and a briefing goes out the moment two sources agree.'}</p>
            </article>
          </div>
        </div>`;
    }
    return html`
      <div class="rise-in">
        <div class="map-drill-head">
          <strong>${country}</strong>
          <${FollowButton} country=${country} />
        </div>
        <div class="map-market-panel">
          <div><span>FX indicator</span><strong>${fx.pair || '—'}</strong><p>${fx.rate_label || 'Watch'} · ${fx.indicator || 'FX watch'}</p></div>
          <div><span>Market layer</span><strong>${marketLabel}</strong><p>${snapshot.data_status || market.status || 'source watch'} </p></div>
          <div><span>Finance signal</span><strong>${snapshot.focus || fx.signal || 'Signals, official notices, and local context'}</strong><p>${marker.finance_signal || marker.ranking_rationale || 'Ranking appears when a live signal is active.'}</p></div>
        </div>
        <${LifecyclePanel} marker=${marker} />
        <${CountryNews} country=${country} marker=${marker} />
        <div class="map-drill-grid">
          ${(() => {
            // A reader with a lens sees their own lane first; everyone else
            // keeps the desk's order.
            const lens = (typeof prefs !== 'undefined' && prefs.lens) || '';
            const ordered = lens
              ? [...items].sort((a, b) =>
                  ((b.persona_label || '') === lens ? 1 : 0) - ((a.persona_label || '') === lens ? 1 : 0))
              : items;
            // One signal routed to six personas rendered as six identical cards.
            // Keep the first, and carry the other recipients on it, so the panel
            // says "also routed to" instead of repeating itself.
            const byTitle = new Map();
            for (const d of ordered) {
              const key = (d.title || '').trim().toLowerCase();
              if (!byTitle.has(key)) byTitle.set(key, { ...d, alsoRouted: [] });
              else {
                const seen = byTitle.get(key);
                const who = d.persona_label || '';
                if (who && who !== seen.persona_label && !seen.alsoRouted.includes(who)) seen.alsoRouted.push(who);
              }
            }
            return [...byTitle.values()].slice(0, 6);
          })().map((d, index) => {
            const rawConfidence = Number(d.confidence_score);
            const conf = Number.isFinite(rawConfidence) ? Math.max(0, Math.min(100, rawConfidence)) : 0;
            const mine = !!((typeof prefs !== 'undefined' && prefs.lens) && (d.persona_label || '') === prefs.lens);
            const color = MAP_COLORS[(d.signal_kind || '').includes('invest') ? 'investment' : (d.signal_kind || '').includes('climate') ? 'climate' : (d.signal_kind || '').includes('procure') ? 'procurement' : 'none'];
            return html`
              <article key=${d.dispatch_id || index} class=${`rise-in drill-card${mine ? ' for-you' : ''}`} style=${{ animationDelay: `${index * 70}ms` }}>
                <span>
                  ${d.dispatch_id || 'Dispatch'} · ${d.persona_label || 'Desk recipient'}
                  ${mine ? html`<span class="for-you-tag">For you</span>` : null}
                </span>
                <h3>${d.title || 'Opportunity briefing'}</h3>
                <p>${d.recommended_action || 'Open the supporting evidence before acting.'}</p>
                ${d.alsoRouted && d.alsoRouted.length
                  ? html`<p class="drill-also">Also routed to ${d.alsoRouted.join(', ')}</p>`
                  : null}
                <div class="conf-row">
                  <div class="conf-track" role="img" aria-label=${`Confidence: ${conf} of 100`}>
                    <div class="conf-fill" style=${{ width: `${conf}%`, background: color }}></div>
                  </div>
                  <span class="conf-num">${conf}/100</span>
                </div>
              </article>`;
          })}
        </div>
      </div>`;
  }

  const node = document.getElementById('map-drill');
  if (!node) return null;
  const root = ReactDOM.createRoot(node);
  root.render(html`<${DrillPanel} country=${null} />`);
  return { render: c => root.render(html`<${DrillPanel} country=${c} />`) };
}

// Current drill selection, so a preference change can repaint the open panel
// without the reader having to tap the country again.
let drillCountry = null;
export function renderDrill(): void {
  if (drillReact) drillReact.render(drillCountry);
}

export function openCountryDrill(country: string): void {
  drillCountry = country;
  document.querySelectorAll('.sig-marker').forEach(x => x.classList.toggle('selected', x.dataset.country === country));
  if (drillReact) { drillReact.render(country); return; }
  const items = MAP_DISPATCHES[country] || [];
  const marker = MAP_MARKER_BY_COUNTRY[country] || {};
  const drill = document.getElementById('map-drill');
  drill.innerHTML = '<div class="map-drill-head"><strong>' + escapeMapText(country) + '</strong><span>' + items.length + ' dispatches</span></div>' +
    (items.length ? '<div class="map-drill-grid">' + items.slice(0, 6).map(d => '<article><span>' + escapeMapText(d.dispatch_id) + ' · ' + escapeMapText(d.persona_label) + '</span><h3>' + escapeMapText(d.title) + '</h3><p>' + escapeMapText(d.recommended_action) + '</p></article>').join('') + '</div>'
                 : '<div class="map-drill-grid"><article><span>WATCHLIST · ' + escapeMapText(marker.confidence || 0) + '/100</span><h3>' + escapeMapText(marker.summary || 'Regional market watch') + '</h3><p>' + escapeMapText(marker.ranking_rationale || 'Nothing confirmed yet — we watch official notices, currency pressure, and market sources here.') + '</p></article></div>');
}

const mapMarkerRefs = {};

function sigIcon(entry, idx) {
  const conf = Math.max(0, Math.min(100, entry.confidence || 0));
  const d = Math.round(14 + conf / 100 * 14);
  const color = MAP_COLORS[entry.kind] || MAP_COLORS.none;
  const quiet = entry.kind === 'none' || conf === 0 ? ' quiet' : '';
  return L.divIcon({
    className: '',
    iconSize: [d, d],
    iconAnchor: [d / 2, d / 2],
    html: '<div class="sig-marker' + quiet + '" data-country="' + escapeMapText(entry.country) + '"' +
          ' style="--c:' + color + ';--delay:' + (idx % 3) * 0.85 + 's;width:' + d + 'px;height:' + d + 'px">' +
          '<span class="sig-ring"></span><span class="sig-dot"></span></div>'
  });
}

function sigTip(entry) {
  const fx = entry.fx || {};
  const market = entry.market || {};
  const marketLine = market.code ? '<br><em>' + escapeMapText(market.code) + ' · ' + escapeMapText((market.snapshot || {}).headline || market.name || 'market watch') + '</em>' : '';
  const fxLine = fx.pair ? '<br><em>FX ' + escapeMapText(fx.pair) + ' · ' + escapeMapText(fx.rate_label || 'watch') + '</em>' : '';
  return '<strong>' + escapeMapText(entry.country) + '</strong>' +
         escapeMapText(entry.summary || entry.top_signal_summary || 'On the watchlist — no current signal') + fxLine + marketLine;
}

function renderMapFallback() {
  const shell = document.querySelector('.map-shell');
  // The expand control lives inside the shell, so lift it out before the
  // fallback overwrites the shell's contents and put it back after.
  const expand = shell.querySelector('.map-expand');
  shell.innerHTML = '<div class="map-fallback">' + MAP_MARKERS.map(m =>
    '<button data-country="' + escapeMapText(m.country) + '" style="--c:' + (MAP_COLORS[m.kind] || MAP_COLORS.none) + '"><i></i>' + escapeMapText(m.country) + '</button>'
  ).join('') + '</div>';
  shell.querySelectorAll('button').forEach(b => b.addEventListener('click', () => openCountryDrill(b.dataset.country)));
  if (expand) shell.appendChild(expand);
}

// Expanded map. Rather than building a second Leaflet instance, the live
// .map-shell and #map-drill are moved into the overlay and returned to
// placeholder comments on close — markers, zoom and the current selection all
// survive because it is the same map the whole time.
let leafletMap = null;

function setupMapOverlay() {
  const overlay = document.getElementById('map-overlay');
  const stage = document.getElementById('map-overlay-stage');
  const openBtn = document.getElementById('map-expand');
  const closeBtn = document.getElementById('map-overlay-close');
  const shell = document.querySelector('.map-shell');
  const drill = document.getElementById('map-drill');
  if (!overlay || !stage || !openBtn || !closeBtn || !shell || !drill) return;

  const shellHome = document.createComment('map-shell');
  const drillHome = document.createComment('map-drill');
  let lastFocus = null;

  // Reframe rather than just resize. invalidateSize alone keeps the old zoom,
  // so expanding just revealed more ocean around the same-sized islands
  // instead of showing the region larger.
  function reframe() {
    if (!leafletMap) return;
    leafletMap.invalidateSize();
    const points = (typeof MAP_MARKERS !== 'undefined' ? MAP_MARKERS : []).map(m => [m.lat, m.lng]);
    if (points.length) leafletMap.fitBounds(L.latLngBounds(points).pad(0.18), { animate: false });
  }

  function openOverlay() {
    if (!overlay.hidden) return;
    lastFocus = document.activeElement;
    shell.before(shellHome);
    drill.before(drillHome);
    stage.append(shell, drill);
    overlay.hidden = false;
    document.body.classList.add('map-overlay-open');
    openBtn.setAttribute('aria-expanded', 'true');
    // The page behind is locked, so the wheel belongs to the map now.
    if (leafletMap) leafletMap.scrollWheelZoom.enable();
    requestAnimationFrame(() => { reframe(); closeBtn.focus(); });
  }

  function closeOverlay() {
    if (overlay.hidden) return;
    shellHome.replaceWith(shell);
    drillHome.replaceWith(drill);
    overlay.hidden = true;
    document.body.classList.remove('map-overlay-open');
    openBtn.setAttribute('aria-expanded', 'false');
    if (leafletMap) leafletMap.scrollWheelZoom.disable();
    requestAnimationFrame(reframe);
    (lastFocus instanceof HTMLElement ? lastFocus : openBtn).focus();
  }

  openBtn.addEventListener('click', openOverlay);
  closeBtn.addEventListener('click', closeOverlay);
  overlay.addEventListener('mousedown', event => { if (event.target === overlay) closeOverlay(); });
  addEventListener('resize', () => { if (!overlay.hidden) reframe(); });
  document.addEventListener('keydown', event => {
    if (overlay.hidden) return;
    if (event.key === 'Escape') { event.preventDefault(); closeOverlay(); return; }
    if (event.key !== 'Tab') return;
    const focusable = [...overlay.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')]
      .filter(el => el.offsetWidth || el.offsetHeight || el === document.activeElement);
    if (!focusable.length) return;
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
}

function initLeaflet() {
  if (typeof L !== 'undefined') {
    const map = L.map('leaflet-map', {
      minZoom: 4, maxZoom: 9,
      scrollWheelZoom: false,
      maxBounds: [[-2, -98], [32, -42]], maxBoundsViscosity: 0.8,
      attributionControl: true
    });
    map.fitBounds(L.latLngBounds(MAP_MARKERS.map(m => [m.lat, m.lng])).pad(0.18));
    // CARTO's keyless raster tiles now return an "API KEY REQUIRED" watermark
    // instead of map imagery, which stamped that text across the homepage map.
    // Esri's World Light Gray Canvas is keyless and muted, so the signal pulses
    // stay the loudest thing on the map.
    L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; <a href="https://www.esri.com/">Esri</a> &mdash; Esri, DeLorme, NAVTEQ',
      maxZoom: 9
    }).addTo(map);
    leafletMap = map;

    MAP_MARKERS.forEach((entry, idx) => {
      const m = L.marker([entry.lat, entry.lng], { icon: sigIcon(entry, idx), keyboard: true, title: entry.country });
      m.bindTooltip(sigTip(entry), { className: 'sig-tip', direction: 'top', offset: [0, -10], opacity: 1 });
      m.on('click', () => {
        openCountryDrill(entry.country);
        map.flyTo([entry.lat, entry.lng], Math.max(map.getZoom(), 6), { duration: 0.7 });
        if (innerWidth < 800) {
          const drill = document.getElementById('map-drill');
          if (drill) setTimeout(() => drill.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 350);
        }
      });
      m.addTo(map);
      mapMarkerRefs[entry.country] = { marker: m, idx };
    });

    fetch('/api/map-data').then(r => r.ok ? r.json() : null).then(entries => {
      if (!entries) return;
      entries.forEach(entry => {
        const ref = mapMarkerRefs[entry.country];
        if (!ref) return;
        const current = MAP_MARKER_BY_COUNTRY[entry.country] || {};
        const merged = { ...current, country: entry.country, confidence: entry.confidence, kind: entry.kind, summary: entry.top_signal_summary || current.summary, ranking_rationale: entry.ranking_rationale || current.ranking_rationale };
        ref.marker.setIcon(sigIcon(merged, ref.idx));
        ref.marker.setTooltipContent(sigTip(merged));
      });
    }).catch(() => {});
  } else {
    renderMapFallback();
  }
}

export function initMap(): void {
  drillReact = createDrillReact();
  initLeaflet();
  setupMapOverlay();
}
