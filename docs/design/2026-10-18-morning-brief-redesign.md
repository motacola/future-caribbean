# Abeng homepage: from portal to morning brief

Status: **built locally**, 18 Oct 2026, by Claude Code with the Hermes frontend-design skill (uncommitted). Recorded as DESIGN.md r5 draft. Deviations: no rail map (map stays on /desk); News wire links to /desk#regional-news instead of a new /news page; Value Flash not used (no previous-cycle values to compare).

## Problem
Feedback: the homepage reads like Yahoo/MSN. Observed on `feat/mobile-engagement-pass` (local dev, 1440px): page is 11,217px tall (mobile 21,602px) and stacks ~15 equal-weight modules — masthead + nav, scrolling LIVE WIRE ticker, second nav row, hero + lead card, map, 23-row score table, four boxed tiles, legend, 13 source labels, empty "tap a country" panel, reading-as dropdown, News Desk with "139 ARTICLES TRACKED" badge + 9 chips + endless 3-column photo card grid, Market Watch, Ask, plus a floating ASK pill and bottom dock.
Captures: `current-home-2026-10-18-top.png`, `current-home-2026-10-18-news.png`.

Jev (advisory, text state only — not usability evidence), probability each element drives the portal feel:
- 3-column photo card grid **0.87**
- no single dominant hierarchy **0.85**
- article count + topic chips **0.76**
- ticker **0.72**, stacked nav rows **0.72**
- score table 0.63, map 0.56, floating pill/dock 0.55

Direction choice (Jev `choose`): **Morning brief 0.65**, Atlas/map-led 0.35, Terminal 0.00, Tidy-current 0.00.

## Direction: a daily briefing, not a front page
FT FirstFT / Economist Espresso discipline. The page is one thing read top to bottom; everything else is one click away.

Stitch concept (project `11120887499683594596`, screen `11e1ac5b9d224b2087d48e1d64e20c27`): `stitch-morning-brief-2026-10-18.png`, ~3,350px tall. Jev on the concept: still reads as portal **0.09**; primary action obvious **0.79**.
**Stitch copy, figures, handles and photos are invented — never ship them.** Borrow structure only.

### Page order
1. **Slim masthead, one row.** Wordmark left, edition date + cycle right, ≤4 text links. Delete the second tab row and the ticker.
2. **Lead dispatch.** Playfair headline, 2–3 sentence standfirst, then ruled *Why it matters / What to watch / Evidence* blocks, one mono source line. Data: existing lead from `outbox/dispatch_desk.json`.
3. **Five moves this cycle.** Numbered 01–05, country in gold small caps, one-sentence headline, source line, hairline rules, **no images**. Replaces "Also this cycle" and the news grid on the homepage.
4. **From the ground (Instagram).** Max **3** posts, square, handle + one-line caption + link to the post. Hard cap: Jev puts regrowth-into-portal risk at 0.75 if it grows. Text-first when no image (DESIGN.md r4 rule still applies).
5. **Country index.** 23 territories as a ruled two-column text list, one status word each, `›` affordance. Tapping opens the country view.
6. **Right rail (desktop, sticky):** small monochrome map + "Ask the desk" input. Mobile: map collapses below the index; Ask moves into the masthead.

### Moves off the homepage
Full Regional News wire (chips, 139-article grid) → its own `/news` page. Market Watch → `/market-momentum` (already exists). FX/equity tiles, source-label row, legend, reading-as dropdown → country view or `/under-the-hood`. Floating ASK pill + bottom dock → removed (Ask lives in rail/masthead).

### Keep
DESIGN.md tokens (paper `#FFF9F0`, ink, teal, gold, oxblood), Playfair/Inter/Plex Mono roles, ruled tables not chips, 4.5:1 control contrast, visible control affordance, publisher-only photos, Astro stack.

## interior.dev components (`http://127.0.0.1:5197/docs`)
Abeng's homepage has no React islands, no `motion`, no Tailwind. Port each component's **timing values and behaviour** into `.astro` + CSS/WAAPI; add a React island + `motion` only where interaction genuinely needs it (frontend-design rule 4).

| Use | Where | Notes |
|---|---|---|
| Text Reveal | lead headline + standfirst, once on load | word split, 0.055s stagger, 1.6s cap, ease `[0.23,1,0.32,1]`, `y:10 blur(8px)`→0. Keep sr-only full text; reduced motion = instant. Only the lead — not every heading. |
| Streaming Text | Ask the desk answer | answers are deterministic; stream for pacing only, citations appear last. |
| Command Palette | Ask / navigate (⌘K) | replaces floating pill + dock. Only candidate for a React island. |
| Reading Progress | thin rule under masthead | covers the briefing column only. |
| Scroll Spy | desktop rail: Lead · Five moves · From the ground · Index | |
| Show More | Evidence block, long standfirsts | no modals. |
| Blur-up Image | Instagram + publisher photos | keep broken-image → text-first fallback. |
| Lightbox | tap an Instagram post | link out to Instagram as well. |
| Value Flash | figures that changed since last cycle (country index status, Market Watch page) | only on real change between cycles. |
| Hide on Scroll | masthead on mobile | do not gate behind reduced-motion (frontend-design rule). |
| Sortable Table | `/market-momentum`, country index page | not on the brief. |

Do **not** use: Logo Marquee (it is the ticker again), New Items Pill, Live Activity, Presence Avatars, Snap Carousel, Like Burst, Filter Grid — each pushes back toward portal.

## Instagram status (needs Chris)
`scripts/enrich_news_images.py` handles `source_platform == "instagram"`, but local `data/regional_news/latest.json` and `public/regional_news.json` contain **0** Instagram items right now. Confirm which branch/feed carries the integration before building section 4. Hindsight: Graph API keyword search is not planned; Public Content Access approval for editorial use is unknown.

## Acceptance (Hermes)
- Homepage ≤ ~4,000px at 1440px; no ticker, no chip rows, no card grid, single nav row.
- `tests/e2e/design-pass.spec.ts` + full desktop/mobile Playwright pass; update specs that assert removed modules rather than deleting coverage.
- Reduced-motion: all reveals instant; no layout state gated on it.
- Screens at 390 / 768 / 1440 inspected; Jev re-check on the built page (advisory).
- No invented figures; every number traces to desk artifacts.
- Local only. No commit/push/deploy without Chris.
