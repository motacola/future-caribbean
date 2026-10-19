// Headline word reveal, map parallax, scroll progress, desk-nav scrollspy,
// section reveal and proof-band counters.
export function initMotion(): void {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduced) return;

  const headline = document.querySelector('.front-lede h1');
  if (headline) {
    let wi = 0;
    const wrap = node => {
      if (node.nodeType === 3) {
        const frag = document.createDocumentFragment();
        node.textContent.split(/(\s+)/).forEach(part => {
          if (!part.trim()) { frag.appendChild(document.createTextNode(part)); return; }
          const s = document.createElement('span');
          s.className = 'hw'; s.style.setProperty('--wd', (wi++ * 0.07) + 's');
          s.textContent = part;
          frag.appendChild(s);
        });
        node.parentNode.replaceChild(frag, node);
      } else if (node.nodeType === 1) {
        const s = document.createElement('span');
        s.className = 'hw'; s.style.setProperty('--wd', (wi++ * 0.07) + 's');
        node.parentNode.replaceChild(s, node);
        s.appendChild(node);
      }
    };
    [...headline.childNodes].forEach(wrap);
  }


// Map parallax: subtle depth drift while the hero is on screen.
const mapShell = document.querySelector('.map-hero .front-map .map-shell');
let parallaxTicking = false;
window.addEventListener('scroll', () => {
  if (parallaxTicking || !mapShell) return;
  parallaxTicking = true;
  requestAnimationFrame(() => {
    const rect = mapShell.parentElement.getBoundingClientRect();
    const vh = window.innerHeight;
    if (rect.bottom > 0 && rect.top < vh) {
      const progress = Math.min(1, Math.max(0, (vh - rect.top) / (vh + rect.height)));
      mapShell.style.setProperty('--map-parallax', ((0.5 - progress) * 14).toFixed(1) + 'px');
    }
    parallaxTicking = false;
  });
}, { passive: true });

  const bar = document.getElementById('scroll-progress');
  const mast = document.querySelector('.masthead');
  const desknav = document.querySelector('.desknav');
  let ticking = false;
  addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      const max = document.documentElement.scrollHeight - innerHeight;
      if (bar) bar.style.width = (max > 0 ? (scrollY / max * 100) : 0) + '%';
      if (mast) mast.classList.toggle('scrolled', scrollY > 40);
      if (desknav) desknav.classList.toggle('scrolled', scrollY > 40);
      ticking = false;
    });
  }, { passive: true });

  // Scrollspy: highlight the desk nav item for the section in view
  const dnItems = [...document.querySelectorAll('.dn-item[href^="#"]')];
  const dnByTarget = new Map(dnItems.map(a => [a.getAttribute('href').slice(1), a]));
  const spyTargets = [...dnByTarget.keys()].map(id => document.getElementById(id)).filter(Boolean);
  if ('IntersectionObserver' in window && spyTargets.length) {
    const spy = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        dnItems.forEach(a => a.classList.remove('active'));
        const link = dnByTarget.get(e.target.id);
        if (link) {
          link.classList.add('active');
          // Keep the active desk visible without scrollIntoView(), which also
          // scrolls the page viewport back to the sticky navigation bar.
          const scroller = link.parentElement;
          if (scroller) {
            const left = link.offsetLeft;
            const right = left + link.offsetWidth;
            if (left < scroller.scrollLeft) scroller.scrollTo({ left: Math.max(0, left - 12), behavior: 'smooth' });
            else if (right > scroller.scrollLeft + scroller.clientWidth) scroller.scrollTo({ left: right - scroller.clientWidth + 12, behavior: 'smooth' });
          }
        }
      });
    }, { rootMargin: '-25% 0px -65% 0px' });
    spyTargets.forEach(t => spy.observe(t));
  }

  const lwRail = document.getElementById('lw-rail');
  if (lwRail) {
    const n = lwRail.children.length || 1;
    document.querySelector('.livewire').style.setProperty('--lw-dur', Math.max(30, n * 7) + 's');
    // These used to preventDefault and open the country drill instead of
    // following the link. Two ways that failed the reader. A country the map
    // does not carry — CARICOM, Caribwide, Nicaragua, Turks and Caicos — has no
    // entry in MAP_DISPATCHES, so the click produced the generic "Nothing
    // confirmed yet" card: a third of the wire opened nothing. And even when
    // the country did resolve, the panel was the country's, headed by whichever
    // dispatch sorted first — click "Barbados: +34.8% foreign investment
    // momentum validated" and you got "Early signal in Barbados, no detail yet".
    // Either way the headline you clicked was not what opened.
    //
    // The href now points at that dispatch's own page, so the link needs no
    // help: it opens the story, survives middle-click and open-in-new-tab, and
    // works with JavaScript off. The country drill keeps its own entry points —
    // the map markers and the fallback buttons.
  }

  if (!('IntersectionObserver' in window)) return;
  const sections = document.querySelectorAll('.sec, .map-hero, .theater, .proof-band, .coordination-strip');
  const CHILD_SEL = '.proof-cell, .aud, .out-panel, .cluster-card, .coord-step, .sig-row, .vpack-col, .route-lane';
  sections.forEach(s => {
    s.classList.add('reveal');
    s.querySelectorAll(CHILD_SEL).forEach((c, i) => {
      c.classList.add('stagger-child');
      c.style.setProperty('--sd', (Math.min(i, 8) * 0.07) + 's');
    });
  });
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      e.target.classList.add('in');
      io.unobserve(e.target);
      if (e.target.classList.contains('proof-band')) animateCounters(e.target);
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  sections.forEach(s => io.observe(s));

  // Safety net: reveal anything still hidden shortly after load. The .reveal class
  // starts sections at opacity:0; if the observer never fires (mobile scroll/resize
  // quirks, JS timing, lazy sections), content would stay invisible forever. This
  // guarantees the page is fully visible even when the enhancement fails.
  const revealAll = () => sections.forEach(s => s.classList.add('in'));
  setTimeout(revealAll, 1200);
  window.addEventListener('load', () => setTimeout(revealAll, 400));

  // The count-up overwrites the real figure while it runs, so it must be
  // guaranteed to land on the true value. requestAnimationFrame is throttled in
  // background tabs and can stop mid-count, which would leave "4 markets
  // watched" on screen when the answer is 23 — on a data page a stale number is
  // worse than no animation. Every counter keeps its final text and a timer
  // writes it back whether or not the frames ever arrive.
  function animateCounters(band) {
    const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    band.querySelectorAll('.proof-k').forEach(el => {
      const finalText = el.textContent;
      const m = finalText.match(/^(\d+)(.*)$/);
      if (!m) return;
      const target = parseInt(m[1], 10), suffix = m[2];
      if (!target || reduced) return;
      const dur = 900;
      const settle = () => { el.textContent = finalText; };
      const t0 = performance.now();
      (function tick(now) {
        const p = Math.min(1, (now - t0) / dur);
        if (p >= 1) { settle(); return; }
        el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3))) + suffix;
        requestAnimationFrame(tick);
      })(t0);
      setTimeout(settle, dur + 400);
    });
  }
}
