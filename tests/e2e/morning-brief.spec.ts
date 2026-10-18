import { test, expect } from '@playwright/test';

// The homepage is a morning brief, not a portal (docs/design/2026-10-18-
// morning-brief-redesign.md). These guard the things that made it read like
// Yahoo/MSN from creeping back, and the affordance/contrast rules in DESIGN.md.

test('homepage stays a brief: one wire ticker, no chip rows, card grid or floating widgets', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  await expect(page.locator('[role="marquee"]')).toHaveCount(1);
  for (const sel of ['.news-grid', '.news-filters', '.track-filter', '.guide-fab', '.desknav']) {
    await expect(page.locator(sel), sel).toHaveCount(0);
  }
  await expect(page.locator('nav[aria-label="Sections"]')).toHaveCount(1);
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const width = page.viewportSize()!.width;
  // Old homepage: 11,217px desktop / 21,602px mobile.
  expect(height).toBeLessThan(width < 600 ? 5000 : 4000);
});

test('lead, moves and country index render from desk data and link out', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1#bm-lead-title')).toHaveCount(1);
  // Full headline is in the accessible name even though words animate.
  const name = await page.locator('h1#bm-lead-title .sr-only').textContent();
  expect((name || '').trim().length).toBeGreaterThan(5);
  const moves = page.locator('.bm-move-row');
  expect(await moves.count()).toBeGreaterThan(0);
  expect(await moves.count()).toBeLessThanOrEqual(5);
  await expect(page.locator('.bm-move-title', { hasText: /no detail yet/i })).toHaveCount(0);
  await expect(page.locator('.bm-index-row')).toHaveCount(23);
  for (const href of await page.locator('.bm-move-row, .bm-index-row').evaluateAll(els => els.map(e => e.getAttribute('href')))) {
    expect(href).toMatch(/^\/(signal\/[^/]+\/|desk#)/);
  }
});

test('From the ground shows at most three real posts, or nothing', async ({ page }) => {
  await page.goto('/');
  const posts = await page.locator('.bm-post').count();
  expect(posts).toBeLessThanOrEqual(3);
  if (posts === 0) await expect(page.locator('#brief-ground')).toHaveCount(0);
  for (const href of await page.locator('.bm-post a').evaluateAll(els => els.map(e => (e as HTMLAnchorElement).href))) {
    expect(href).toMatch(/^https:\/\/(www\.)?instagram\.com\//);
  }
});

test('control and label text clears 4.5:1 against its own backdrop', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  const failures = await page.evaluate(() => {
    const parse = (c: string) => (c.match(/[\d.]+/g) || []).map(Number);
    const lum = ([r, g, b]: number[]) => {
      const f = (v: number) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    const backdrop = (el: Element | null): number[] => {
      for (; el; el = el.parentElement) {
        const c = parse(getComputedStyle(el).backgroundColor);
        if (c.length === 3 || (c.length === 4 && c[3] === 1)) return c.slice(0, 3);
      }
      return [255, 249, 240];
    };
    const sel = '.bm-link,.bm-ask-btn,.bm-edition,.bm-kicker,.bm-label,.bm-fine,.bm-num,.bm-country,.bm-status,.bm-section-link,.bm-section-note,.bm-spy a,.bm-go,.bm-more-btn,.bm-ask-row button,.bm-wire .lw-kicker,.bm-wire-label';
    const bad: string[] = [];
    for (const el of document.querySelectorAll(sel)) {
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      const fg = lum(parse(getComputedStyle(el).color).slice(0, 3));
      const bg = lum(backdrop(el));
      const ratio = (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05);
      if (ratio < 4.5) bad.push(`${el.className} "${(el.textContent || '').trim().slice(0, 20)}" ${ratio.toFixed(2)}`);
    }
    return [...new Set(bad)];
  });
  expect(failures).toEqual([]);
});

test('⌘K opens the interior.dev command palette and jumps to a country', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  await page.keyboard.press('ControlOrMeta+k');
  const box = page.getByRole('combobox', { name: 'Ask the desk or jump to a country' });
  await expect(box).toBeVisible();
  await box.fill('guy');
  const option = page.getByRole('option', { name: /Guyana/ });
  await expect(option).toBeVisible();
  await option.click();
  await expect(page).toHaveURL(/\/(signal\/[^/]+\/|desk)/);
});

test('the brief\'s reading aids work: headline text, scroll spy, show more, reading progress', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  // The word-by-word reveal keeps the whole headline readable to assistive tech.
  await expect(page.locator('#bm-lead-title .sr-only')).toHaveText(/\S/);
  if (page.viewportSize()!.width > 960) {
    const spy = page.getByRole('navigation', { name: 'On this page' });
    await expect(spy).toBeVisible();
    await page.locator('#brief-index').scrollIntoViewIfNeeded();
    await expect(spy.locator('a[aria-current]')).toHaveAttribute('data-spy', /brief-(index|moves)/);
  }
  await page.evaluate(() => scrollTo(0, 1600));
  await expect.poll(() => page.locator('#bm-progress-bar').evaluate(el => getComputedStyle(el).transform)).not.toBe('matrix(0, 0, 0, 1, 0, 0)');
  // Show More is the interior.dev component; wait for it to hydrate first.
  await expect(page.locator('astro-island[component-export="EvidenceMore"]:not([ssr])')).toHaveCount(1);
  const more = page.locator('.bm-showmore button[aria-controls]');
  if (await more.isVisible()) {
    await more.click();
    await expect(more).toHaveAttribute('aria-expanded', 'true');
  }
});

test('reduced motion shows the headline immediately', async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: 'reduce' });
  const page = await ctx.newPage();
  await page.goto('/');
  expect(await page.locator('.bm-word').first().evaluate(el => getComputedStyle(el).animationName)).toBe('none');
  await ctx.close();
});

test('the wire ticker links each headline to its dispatch and pauses for reduced motion', async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: 'reduce' });
  const page = await ctx.newPage();
  await page.goto('/');
  const items = page.locator('.bm-wire-rail:not([aria-hidden]) .lw-item');
  expect(await items.count()).toBeGreaterThan(0);
  for (const href of await items.evaluateAll(els => els.map(e => e.getAttribute('href')))) {
    expect(href).toMatch(/^\/(signal\/[^/]+\/|desk#)/);
  }
  expect(await page.locator('.bm-wire-rail').first().evaluate(el => getComputedStyle(el).animationName)).toBe('none');
  await expect(page.locator('.bm-wire-rail[aria-hidden]')).toBeHidden();
  await ctx.close();
});

test('the map is the hero: first thing under the wire, 23 pins, a country card in place', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  const map = page.locator('#bm-map');
  await expect(map).toBeVisible();
  const box = await map.boundingBox();
  // Above the fold and the widest thing on the page.
  expect(box!.y).toBeLessThan(200);
  expect(box!.width).toBeGreaterThanOrEqual(page.viewportSize()!.width - 1);
  expect(box!.height).toBeGreaterThanOrEqual(360);
  await expect(page.locator('#bm-map .leaflet-marker-icon')).toHaveCount(23);
  await page.locator('.leaflet-marker-icon[title="Guyana"]').click();
  const card = page.locator('#bm-map-card');
  await expect(card).toBeVisible();
  await expect(card.locator('.bm-card-title')).toHaveText('Guyana');
  await expect(card.locator('a.bm-go')).toHaveAttribute('href', /^\/(signal\/[^/]+\/|desk#)/);
  await card.locator('.bm-card-close').click();
  await expect(card).toBeHidden();
});
