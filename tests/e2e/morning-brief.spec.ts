import { test, expect } from '@playwright/test';

// The homepage is a morning brief, not a portal (docs/design/2026-10-18-
// morning-brief-redesign.md). These guard the things that made it read like
// Yahoo/MSN from creeping back, and the affordance/contrast rules in DESIGN.md.

test('homepage stays a brief: no ticker, chip rows, card grid or floating widgets', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  for (const sel of ['.livewire', '[role="marquee"]', '.news-grid', '.news-filters', '.track-filter', '.guide-fab', '.desknav']) {
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
    const sel = '.bm-link,.bm-ask-btn,.bm-edition,.bm-kicker,.bm-label,.bm-fine,.bm-num,.bm-country,.bm-status,.bm-section-link,.bm-section-note,.bm-spy a,.bm-go,.bm-more-btn,.bm-ask-row button';
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

test('⌘K palette jumps to a country and offers Ask', async ({ page }) => {
  await page.goto('/');
  await page.locator('#bm-palette-open').click();
  await expect(page.locator('#bm-palette')).toBeVisible();
  await page.locator('#bm-palette-input').fill('guy');
  await expect(page.locator('#bm-palette-list li').first()).toContainText('Guyana');
  await expect(page.locator('#bm-palette-list li').last()).toContainText('Ask the desk');
  await page.keyboard.press('Escape');
  await expect(page.locator('#bm-palette')).toBeHidden();
});

test('reduced motion shows the headline immediately', async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: 'reduce' });
  const page = await ctx.newPage();
  await page.goto('/');
  const anim = await page.locator('.bm-word').first().evaluate(el => getComputedStyle(el).animationName);
  expect(anim).toBe('none');
  await ctx.close();
});
