#!/usr/bin/env node
// fallow-ignore-file unused-file
// CLI tool: invoked by hand and by scripts/verify.sh, never imported.
/**
 * Page capture for visual checks. Replaces the throwaway Playwright snippets
 * that were previously written inline each time.
 *
 *   node scripts/shot.mjs out.png                       # full page, sliced
 *   node scripts/shot.mjs out.png --sel '.market-grid'  # one element
 *   node scripts/shot.mjs out.png --mobile
 *   node scripts/shot.mjs out.png --url http://…/build
 *
 * Always reports console/page errors, which is usually the point.
 */
import { chromium } from 'playwright';
import { dirname } from 'path';
import { mkdirSync } from 'fs';

const args = process.argv.slice(2);
const out = args[0];
if (!out) { console.error('usage: shot.mjs <out.png> [--sel S] [--mobile] [--url U]'); process.exit(1); }
const flag = (name, fallback) => { const i = args.indexOf(name); return i > -1 ? args[i + 1] : fallback; };
const has = name => args.includes(name);

const url = flag('--url', 'http://127.0.0.1:4321/');
const sel = flag('--sel', null);
const mobile = has('--mobile');
const viewport = mobile ? { width: 390, height: 844 } : { width: 1440, height: 1000 };

mkdirSync(dirname(out) || '.', { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport, isMobile: mobile, hasTouch: mobile });

// These are Vercel Python functions (api/*.py). `astro preview` serves the
// static build only, so they 404 locally by design and the page guards every
// one with `r.ok ? … : null`. Flagging them would train us to ignore the tool.
const SERVERLESS_ONLY = /\/api\/(map-data|domains|reasoning|status)\b/;

const errors = [];
const expected = [];
page.on('pageerror', e => errors.push(`pageerror: ${e.message}`));
page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(`console: ${m.text()}`); });
page.on('response', r => {
  if (r.status() < 400) return;
  (SERVERLESS_ONLY.test(r.url()) ? expected : errors).push(`${r.status()} ${r.url()}`);
});

await page.goto(url, { waitUntil: 'networkidle' });
// Reveal-on-scroll sections are invisible to a headless capture otherwise.
await page.evaluate(() => document.querySelectorAll('.reveal').forEach(e => e.classList.add('in')));
await page.waitForTimeout(1200);

if (sel) {
  const el = page.locator(sel).first();
  if (!(await el.count())) { console.error(`not found: ${sel}`); await browser.close(); process.exit(1); }
  await el.scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
  await el.screenshot({ path: out });
  console.log(`wrote ${out}  (${sel})`);
} else {
  // Slice rather than one tall image: a 13000px capture is unreadable.
  const height = await page.evaluate(() => document.body.scrollHeight);
  const step = viewport.height - 50;
  let i = 0;
  for (let y = 0; y < height; y += step, i++) {
    await page.evaluate(v => scrollTo(0, v), y);
    await page.waitForTimeout(300);
    await page.screenshot({ path: out.replace(/\.png$/, `-${String(i).padStart(2, '0')}.png`) });
  }
  console.log(`wrote ${i} slices  (page height ${height}px)`);
}

const overflow = await page.evaluate(() =>
  document.documentElement.scrollWidth - document.documentElement.clientWidth);
if (overflow > 0) errors.push(`horizontal overflow: ${overflow}px`);

if (expected.length) console.log(`serverless-only (expected under preview): ${expected.length}`);
console.log(errors.length ? `errors:\n  ${errors.join('\n  ')}` : 'errors: none');
await browser.close();
process.exit(errors.length ? 1 : 0);
