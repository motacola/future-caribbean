import { expect, test } from '@playwright/test';

const forbiddenCopy = [
  'generalised to any emerging-market set',
  'Emerging-Market Capital Flows',
  'guaranteed return',
  'buy recommendation',
];

test('homepage leads with the Caribbean map and decision context before system proof', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Caribbean opportunity');
  await expect(page.locator('#leaflet-map')).toBeVisible();
  await expect(page.locator('#decision-workspace')).toBeVisible();
  await expect(page.locator('#ask-desk')).toBeAttached();
  await expect(page.locator('#receipts')).toBeAttached();
  await expect(page.getByRole('link', { name: 'Build your feed' })).toHaveAttribute('href', '/build');

  const order = await page.evaluate(() => {
    const top = (selector: string) => document.querySelector(selector)?.getBoundingClientRect().top ?? Number.MAX_VALUE;
    return { map: top('.map-hero'), decision: top('#decision-workspace'), receipts: top('#receipts') };
  });
  expect(order.map).toBeLessThan(order.decision);
  expect(order.decision).toBeLessThan(order.receipts);

  for (const copy of forbiddenCopy) {
    await expect(page.getByText(copy, { exact: false })).toHaveCount(0);
  }
});

test('regional movement connects each classified market to its drill', async ({ page }) => {
  await page.goto('/');
  const strip = page.locator('.regional-movement');
  await expect(strip).toBeVisible();
  await expect(strip.locator('.rmv-chip').first()).toBeVisible();
  await expect(page.locator('.map-finance-strip')).toBeVisible();
  await expect(page.locator('#regional-news')).toBeVisible();
});

test('market watch labels dates, source status, and illustrative chart limits honestly', async ({ page }) => {
  await page.goto('/#market-watch');
  const marketWatch = page.locator('#market-watch');
  await expect(marketWatch).toBeVisible();

  const cards = marketWatch.locator('.market-card');
  const charts = marketWatch.locator('.market-chart-card');
  expect(await cards.count()).toBeGreaterThan(0);
  await expect(charts).toHaveCount(await cards.count());
  await expect(cards.locator('.market-observation').first()).toContainText(/Official source (observation|status):/);
  await expect(charts.locator('.market-chart-disclosure').first()).toHaveText(
    'Illustrative indexed activity proxy — not exchange price or OHLC data.',
  );
  await expect(marketWatch.locator('.source-registry')).toBeVisible();
  await expect(marketWatch.getByText(/Latest \d+/)).toHaveCount(0);
});

test('desktop hero map opens a semantic country drill-down', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name.includes('mobile'));
  await page.goto('/');

  const mainMap = page.locator('#leaflet-map');
  await expect(mainMap).toBeVisible();
  expect(await mainMap.evaluate(node => node.getBoundingClientRect().height)).toBeGreaterThanOrEqual(540);

  await page.evaluate(() => {
    const opener = (window as unknown as { openCountryDrill?: (country: string) => void }).openCountryDrill;
    if (!opener) throw new Error('openCountryDrill is not available');
    opener('Guyana');
  });
  await expect(page.locator('#map-drill article.drill-card').first()).toBeVisible();
  await expect(page.locator('#map-drill')).not.toContainText('<article');
});

test('the map never traps page-wheel scrolling', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name.includes('mobile'), 'Mouse-wheel behavior is desktop-specific');
  await page.goto('/');

  const map = page.locator('#leaflet-map');
  await expect(map).toBeVisible();
  await map.click({ position: { x: 300, y: 280 } });
  await page.evaluate(() => window.scrollTo(0, 0));

  const box = await map.boundingBox();
  if (!box) throw new Error('Map bounds are unavailable');
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  for (let step = 0; step < 8; step += 1) {
    await page.mouse.wheel(0, 700);
    await page.waitForTimeout(100);
  }
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(3000);

  await page.keyboard.press('End');
  await expect.poll(() => page.evaluate(() => {
    const footers = Array.from(document.querySelectorAll('footer'));
    const footer = footers[footers.length - 1];
    if (!footer) return false;
    const bounds = footer.getBoundingClientRect();
    return bounds.top < innerHeight && bounds.bottom > 0;
  })).toBe(true);
});

test('mobile homepage is glance-first and has no horizontal overflow', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes('mobile'));
  await page.goto('/');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  await expect(page.locator('.mast-name')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Build your feed' }).first()).toBeVisible();

  const positions = await page.evaluate(() => ({
    map: document.querySelector('.map-hero')?.getBoundingClientRect().top ?? Number.MAX_VALUE,
    decision: document.querySelector('#decision-workspace')?.getBoundingClientRect().top ?? Number.MAX_VALUE,
  }));
  expect(positions.map).toBeLessThan(positions.decision);
});
