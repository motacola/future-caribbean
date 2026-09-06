/**
 * Shared reading tools for the long record pages.
 *
 * These pages had grown into single unbroken walls — /regional-connections
 * ran to 31 screens on a phone, /capability-matches to 19 with 161 controls —
 * with no way to jump, no way to narrow, and lists silently truncated by a
 * server-side .slice() that the page never mentioned.
 *
 * Everything here is progressive enhancement: the markup ships complete and
 * visible, and this only ever hides rows after it has added the control that
 * brings them back. With JS off the page reads exactly as it did before.
 */

/* ── On-this-page navigation ─────────────────────────────── */

function initSectionNav(): void {
  const sections = [...document.querySelectorAll<HTMLElement>('.sec')].filter(
    (s) => s.querySelector('h2.sec-title'),
  );
  if (sections.length < 3) return;

  const nav = document.createElement('nav');
  nav.className = 'page-nav';
  nav.setAttribute('aria-label', 'On this page');

  const list = document.createElement('div');
  list.className = 'page-nav-inner';
  list.innerHTML = '<span class="page-nav-label">On this page</span>';

  const links: HTMLAnchorElement[] = [];
  sections.forEach((sec, i) => {
    const title = sec.querySelector('h2.sec-title');
    if (!title) return;
    if (!sec.id) sec.id = `section-${i + 1}`;
    const a = document.createElement('a');
    a.href = `#${sec.id}`;
    a.textContent = (title.textContent || '').trim();
    a.className = 'page-nav-link';
    list.appendChild(a);
    links.push(a);
  });
  if (links.length < 3) return;

  nav.appendChild(list);
  const main = document.getElementById('main-content');
  (main?.parentNode || document.body).insertBefore(nav, main?.nextSibling || null);

  // Mark the section currently in view so the reader keeps their place.
  if (!('IntersectionObserver' in window)) return;
  const spy = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        const link = links.find((l) => l.getAttribute('href') === `#${e.target.id}`);
        if (!link) return;
        links.forEach((l) => {
          l.classList.remove('is-current');
          l.removeAttribute('aria-current');
        });
        link.classList.add('is-current');
        link.setAttribute('aria-current', 'true');
      });
    },
    { rootMargin: '-15% 0px -70% 0px' },
  );
  sections.forEach((s) => spy.observe(s));
}

/* ── Progressive reveal ──────────────────────────────────── */

function rowsOf(container: HTMLElement): HTMLElement[] {
  return [...container.children].filter(
    (el): el is HTMLElement => el instanceof HTMLElement && !el.classList.contains('reveal-more-wrap'),
  );
}

function initReveal(): void {
  document.querySelectorAll<HTMLElement>('[data-reveal]').forEach((container) => {
    const step = parseInt(container.dataset.reveal || '15', 10);
    const rows = rowsOf(container);
    if (!step || rows.length <= step) return;

    const wrap = document.createElement('div');
    wrap.className = 'reveal-more-wrap';
    const status = document.createElement('p');
    status.className = 'reveal-status';
    status.setAttribute('role', 'status');
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'reveal-more';
    if (!container.id) container.id = `list-${Math.random().toString(36).slice(2, 8)}`;
    btn.setAttribute('aria-controls', container.id);
    wrap.append(status, btn);
    container.after(wrap);

    let shown = step;
    const apply = () => {
      const visible = rowsOf(container).filter((r) => !r.hasAttribute('data-filtered-out'));
      visible.forEach((r, i) => {
        r.hidden = i >= shown;
      });
      const total = visible.length;
      const showing = Math.min(shown, total);
      // How much of the corpus reaches the page at all is stated in the
      // section's own prose; repeating it here read as nonsense once a
      // filter narrowed the list.
      status.textContent = total === 0 ? '' : `Showing ${showing} of ${total}`;
      if (showing >= total) {
        btn.hidden = true;
      } else {
        btn.hidden = false;
        const next = Math.min(step, total - showing);
        btn.textContent = `Show ${next} more`;
      }
    };

    btn.addEventListener('click', () => {
      const before = rowsOf(container).filter((r) => !r.hidden).length;
      shown += step;
      apply();
      // Send focus to the first newly revealed row so keyboard and screen
      // reader users land on the new content, not back at the top.
      const revealed = rowsOf(container).filter((r) => !r.hidden)[before];
      if (revealed) {
        revealed.setAttribute('tabindex', '-1');
        revealed.focus({ preventScroll: true });
      }
    });

    container.addEventListener('abeng:filtered', () => {
      shown = step;
      apply();
    });
    apply();
  });
}

/* ── Filters ─────────────────────────────────────────────── */

function initFilters(): void {
  document.querySelectorAll<HTMLElement>('[data-filter-for]').forEach((bar) => {
    const target = document.querySelector<HTMLElement>(bar.dataset.filterFor || '');
    if (!target) return;
    const selects = [...bar.querySelectorAll<HTMLSelectElement>('select[data-filter-key]')];
    if (!selects.length) return;

    // Options come from the rows themselves, so a filter can never offer a
    // value that matches nothing.
    selects.forEach((sel) => {
      const key = sel.dataset.filterKey!;
      const values = new Set<string>();
      rowsOf(target).forEach((r) => {
        const v = r.dataset[key];
        if (v) v.split('|').forEach((one) => one.trim() && values.add(one.trim()));
      });
      [...values].sort((a, b) => a.localeCompare(b)).forEach((v) => {
        const opt = document.createElement('option');
        opt.value = v;
        opt.textContent = v;
        sel.appendChild(opt);
      });
      if (values.size < 2) sel.closest('.filter-field')?.setAttribute('hidden', '');
    });

    const empty = document.createElement('p');
    empty.className = 'filter-empty';
    empty.hidden = true;
    empty.textContent = 'Nothing matches those filters.';
    target.after(empty);

    const applyFilters = () => {
      let matched = 0;
      rowsOf(target).forEach((row) => {
        const keep = selects.every((sel) => {
          if (!sel.value) return true;
          const v = row.dataset[sel.dataset.filterKey!] || '';
          return v.split('|').map((s) => s.trim()).includes(sel.value);
        });
        if (keep) {
          row.removeAttribute('data-filtered-out');
          matched++;
        } else {
          row.setAttribute('data-filtered-out', '');
          row.hidden = true;
        }
      });
      empty.hidden = matched > 0;
      target.dispatchEvent(new CustomEvent('abeng:filtered'));
    };

    selects.forEach((sel) => sel.addEventListener('change', applyFilters));

    const reset = bar.querySelector<HTMLButtonElement>('.filter-reset');
    reset?.addEventListener('click', () => {
      selects.forEach((s) => (s.value = ''));
      applyFilters();
    });
  });
}

initFilters();
initReveal();
initSectionNav();
