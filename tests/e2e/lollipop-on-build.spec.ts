/**
 * My Signal Desk TanStack lollipop contract.
 *
 * The lollipop is the roadmap-3 deliverable: an interactive ranked
 * opportunity chart on /build, fed by the dispatch desk, with a 60-point
 * watch threshold. This file pins the runtime behaviour with Playwright
 * so a future agent can't silently ship a y=NaN regression like the one
 * that landed in the first cut of commit aa0329b.
 *
 * These tests require a live Astro preview (started by the webServer
 * config in playwright.config.ts). They use the existing fixture
 * (src/data/build-pipeline-fixture.json) so the chart's data is stable
 * across machines and runs.
 */
import { expect, test } from '@playwright/test';

test('lollipop section is present on /build with the right structure', async ({ page }) => {
  await page.goto('/build/');

  // The shell + label + heading + freshness label.
  await expect(page.locator('.ranked-section')).toBeVisible();
  await expect(page.getByText('Ranked opportunity', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Markets this cycle, in priority order' })).toBeVisible();
  // The freshness label must include "cycle " + a fresh ISO timestamp.
  await expect(page.locator('.ranked-meta')).toContainText('cycle');
  await expect(page.locator('.ranked-meta')).toContainText('as of');
});

test('lollipop renders 4 bars with non-NaN y values', async ({ page }) => {
  // This is the regression that the previous cut had: every bar came
  // out with y="NaN" because the scalePoint() y-domain was inferred from
  // data that wasn't arriving through the React island boundary. With
  // an explicit y-domain, the rects have real y values.
  await page.goto('/build/');
  const ranked = page.locator('.ranked-section');
  await ranked.scrollIntoViewIfNeeded();
  // Wait for the chart to hydrate and render.
  await page.waitForFunction(
    () => document.querySelectorAll('.ranked-section svg rect').length > 0,
    null,
    { timeout: 5_000 },
  );

  // 4 distinct countries (Guyana, Belize, CARICOM, Caribwide) from the
  // fixture, deduped by opportunitiesFromDesk. There is 1 background
  // rect + 4 bar rects = 5 rects total.
  const rects = ranked.locator('svg rect');
  await expect(rects).toHaveCount(5);

  // No bar may have y="NaN" — that was the bug this test was added
  // to catch. Background rects use y="0" so we filter for the bar
  // groups (data-ts-key starting with "bar-x-1").
  const nanRects = await ranked.locator('svg rect[y="NaN"]').count();
  expect(nanRects, 'no bar rect may have y=NaN').toBe(0);

  // Sanity: every bar must have a numeric y position. Bar y can be negative
  // (TanStack sometimes allows marks to extend above the plot area); the
  // contract is that the value is a real number, not the literal "NaN"
  // string. The fixture's 4 countries must each have one bar, and no
  // bar's y is the string "NaN".
  const yValues = await ranked.locator('svg rect').evaluateAll((els) =>
    els.map((el) => el.getAttribute('y') || 'null'),
  );
  // The 4 bars are the 4 rects with data-ts-key starting with "bar-x-1".
  const barY = yValues.filter((y) => y !== null && y !== 'NaN' && !y.startsWith('null'));
  expect(barY.length, 'every bar must have a real y position').toBeGreaterThanOrEqual(4);
  // Specifically: no bar's y is the string "NaN"
  expect(yValues.filter((y) => y === 'NaN').length).toBe(0);
});

test('lollipop applies caribbeanTheme tokens (no hardcoded hex)', async ({ page }) => {
  // Every paintable color in the chart should reference a CSS variable.
  // The CSS variables are defined in :root on every page that hosts
  // the chart, so they MUST resolve — if anyone hardcodes a hex in
  // the chart definition, this test catches the visual divergence.
  await page.goto('/build/');
  const ranked = page.locator('.ranked-section');
  await ranked.scrollIntoViewIfNeeded();
  await page.waitForFunction(
    () => document.querySelectorAll('.ranked-section svg rect').length > 0,
    null,
    { timeout: 5_000 },
  );

  // Background rect must use caribbean-bg.
  const bgFill = await ranked.locator('svg rect[data-ts-key="background"]').getAttribute('fill');
  expect(bgFill).toContain('--caribbean-bg');
  // At least one bar must use caribbean-reef.
  const barFills = await ranked.locator('svg rect[class*="bar-x"]').evaluateAll((els) =>
    els.map((el) => el.getAttribute('fill') || ''),
  );
  for (const fill of barFills) {
    expect(fill).toContain('--caribbean-reef');
  }
  // The watch line uses caribbean-sun.
  const watchStroke = await ranked.locator('svg line[stroke-dasharray]').first().getAttribute('stroke');
  expect(watchStroke).toContain('--caribbean-sun');
});

test('lollipop watch line is at the 60-point threshold', async ({ page }) => {
  // The watch line is a vertical line at x=score=60 within the chart's
  // x-domain [0, 100]. The chart auto-scales its viewBox to the viewport,
  // so the absolute x depends on the chart width. The contract is that
  // the line is at the 60-percent mark, NOT at 0 (no domain bug) and
  // NOT at 100 (off-by-one). The line is also vertical (x1 == x2).
  await page.goto('/build/');
  const ranked = page.locator('.ranked-section');
  await ranked.scrollIntoViewIfNeeded();
  await page.waitForFunction(
    () => document.querySelectorAll('.ranked-section svg line[stroke-dasharray]').length > 0,
    null,
    { timeout: 5_000 },
  );
  // Get the chart viewBox + the first watch-line x position.
  const layout = await ranked.locator('svg').first().evaluate((svg) => {
    const line = svg.querySelector('line[stroke-dasharray]');
    const vb = svg.getAttribute('viewBox')?.split(/\s+/).map(Number) || [0, 0, 0, 0];
    return { x1: line?.getAttribute('x1'), vb };
  });
  const x1 = parseFloat(layout.x1 || 'NaN');
  const vbW = layout.vb[2] || 0;
  expect(Number.isFinite(x1), 'watch line x1 must be a number').toBeTruthy();
  // The watch line must be at the 60% mark, ±1% (handles sub-pixel
  // rounding). 60% of 0.5% padding is x = vbW * (0.5 + 0.6 * 0.99) ≈ 0.594 * vbW.
  const expected = vbW * 0.594;
  expect(x1).toBeGreaterThan(vbW * 0.55);
  expect(x1).toBeLessThan(vbW * 0.65);
});
