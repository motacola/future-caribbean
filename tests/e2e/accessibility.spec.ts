import { test, expect } from '@playwright/test';

/**
 * Keyboard and assistive-tech basics that the site lacked entirely.
 *
 * Before these were added: the global stylesheet defined no focus style at
 * all, so most controls gave a keyboard user no indication of where they
 * were; there was no skip link on a home page running to ~25 screens with
 * 226 controls; only /accuracy carried a main landmark; every sub-page
 * jumped straight from h1 to h4, so heading navigation skipped every
 * section boundary; and controls rendered as small as 21px tall on a phone.
 */

const PAGES = [
  '/',
  '/build',
  '/accuracy',
  '/capability-matches',
  '/opportunity-resolution',
  '/regional-connections',
];

for (const path of PAGES) {
  test(`${path} is reachable by keyboard and announces its structure`, async ({ page }) => {
    await page.goto(path);

    // The skip link is the first thing a keyboard user reaches, and it must
    // become visible when it takes focus.
    await page.keyboard.press('Tab');
    const skip = page.locator('.skip-link');
    await expect(skip).toBeFocused();
    await expect(skip).toBeVisible();

    const href = await skip.getAttribute('href');
    expect(href).toBe('#main-content');
    // ...and it must actually land somewhere.
    await expect(page.locator('#main-content')).toHaveCount(1);

    // Focus has to be visible on whatever holds it.
    const outline = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el) return null;
      const cs = getComputedStyle(el);
      return { width: parseFloat(cs.outlineWidth) || 0, style: cs.outlineStyle };
    });
    expect(outline).not.toBeNull();
    expect(outline!.width).toBeGreaterThan(0);
    expect(outline!.style).not.toBe('none');

    // Exactly one main landmark, however it is expressed.
    const mainCount = await page.evaluate(
      () => document.querySelectorAll('main, [role="main"]').length,
    );
    expect(mainCount).toBe(1);

    // One h1, and no skipped level in the outline.
    await expect(page.locator('h1')).toHaveCount(1);
    const jumps = await page.evaluate(() => {
      const levels = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h => +h.tagName[1]);
      const bad: string[] = [];
      for (let i = 1; i < levels.length; i++) {
        if (levels[i] - levels[i - 1] > 1) bad.push(`h${levels[i - 1]}->h${levels[i]}`);
      }
      return [...new Set(bad)];
    });
    expect(jumps).toEqual([]);
  });
}

test('standalone controls are big enough to tap on a phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.waitForTimeout(500);

  // Inline links inside a sentence are exempt (WCAG 2.5.8); these are the
  // standalone controls, which were rendering 21-32px tall.
  const undersized = await page.evaluate(() => {
    const sel = '.chip,.news-filter,.track-btn,.verdict-btn,.theater-toggle,'
      + '.map-expand,.deep-btn,.proof-toggle,.map-fallback button,.mast-links a';
    const bad: string[] = [];
    for (const el of document.querySelectorAll(sel)) {
      const b = el.getBoundingClientRect();
      if (b.height > 0 && b.height < 44) {
        bad.push(`${(el.textContent || '').trim().slice(0, 24)} ${Math.round(b.height)}px`);
      }
    }
    return bad;
  });
  expect(undersized).toEqual([]);
});
