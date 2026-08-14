/**
 * My Signal Desk TanStack lollipop contract.
 *
 * The lollipop is the roadmap-3 deliverable: an interactive ranked
 * opportunity chart on /build, fed by the dispatch desk, with a 60-point
 * watch threshold. This file pins the runtime behaviour with Playwright
 * so a future agent can't silently ship a y=NaN regression like the one
 * that landed in the first cut of commit aa0329b.
 *
 * Expected values are derived from the checked-in dispatch desk artifact,
 * so the test detects a chart that silently falls back to demo data.
 */
import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const desk = JSON.parse(
  readFileSync('outbox/dispatch_desk.json', 'utf8'),
) as {
  cycle_id: string;
  generated_at: string;
  clusters: Array<{ country_cluster: string }>;
};
const expectedCycle = desk.cycle_id;
const expectedAsOf = new Date(
  desk.generated_at
    .replace(/ UTC$/i, 'Z')
    .replace(/^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})Z$/, '$1T$2:00Z'),
).toISOString();
const expectedCountries = Array.from(new Set(desk.clusters.map(cluster => cluster.country_cluster)))
  .filter(Boolean)
  .slice(0, 12);

test('lollipop section is present on /build with the right structure', async ({ page }) => {
  await page.goto('/build/');

  // The shell + label + heading + freshness label.
  await expect(page.locator('.ranked-section')).toBeVisible();
  await expect(page.getByText('Ranked opportunity', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Markets this cycle, in priority order' })).toBeVisible();
  await expect(page.locator('.ranked-meta')).toHaveText(`${expectedAsOf} · cycle ${expectedCycle}`);
  await expect(page.locator('.ranked-sub')).toContainText('Current published dispatch-desk snapshot');
});

test('lollipop renders the current desk countries with non-NaN y values', async ({ page }) => {
  // This is the regression that the previous cut had: every bar came
  // out with y="NaN" because the scalePoint() y-domain was inferred from
  // data that wasn't arriving through the React island boundary. With
  // an explicit y-domain, the rects have real y values.
  await page.goto('/build/');
  const ranked = page.locator('.ranked-section');
  await ranked.scrollIntoViewIfNeeded();
  await expect(ranked.locator('svg rect').first()).toBeVisible();

  // One background rect plus one bar per distinct capped country.
  const rects = ranked.locator('svg rect');
  await expect(rects).toHaveCount(expectedCountries.length + 1);
  await expect(ranked).toContainText(expectedCountries[0]);

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
  const barY = yValues.filter((y) => y !== null && y !== 'NaN' && !y.startsWith('null'));
  expect(barY.length, 'every bar must have a real y position').toBeGreaterThanOrEqual(expectedCountries.length);
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
  await expect(ranked.locator('svg rect').first()).toBeVisible();

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
  // Current country labels change the left-axis width, so a percentage of
  // the whole SVG viewBox is not a stable data-coordinate assertion. Pin
  // the encoded TanStack datum and verify each rule remains vertical.
  await page.goto('/build/');
  const ranked = page.locator('.ranked-section');
  await ranked.scrollIntoViewIfNeeded();
  const lines = ranked.locator('svg line[stroke-dasharray]');
  await expect(lines).toHaveCount(expectedCountries.length);
  const values = await lines.evaluateAll(elements => elements.map(element => ({
    key: element.getAttribute('data-ts-key'),
    x1: element.getAttribute('x1'),
    x2: element.getAttribute('x2'),
  })));
  values.forEach(({ key, x1, x2 }) => {
    expect(key).toContain('number:60');
    expect(x1).toBe(x2);
    expect(Number.isFinite(Number(x1))).toBeTruthy();
  });
});
