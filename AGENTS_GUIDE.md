# Agent guide for the Abeng Astro site

This file is for AI agents (Claude Code, Codex, OpenCode, Pi, etc.) working on
this repo. It does NOT replace `AGENTS.md` (which is the product contract);
it complements it with implementation-grade conventions so a fresh agent can
ship a verified change in 30 minutes instead of 2 hours of archaeology.

Read this before editing anything in `src/`. If you only have a one-line
fix to make, the Quick orientation + Build / test / verify sections are
enough. The rest is for new features, refactors, and the chart path.

## Quick orientation

| What | Where | Read when |
|------|-------|-----------|
| Astro pages | `src/pages/index.astro`, `src/pages/build.astro`, `src/pages/regional-connections.astro` | You are editing a page |
| Data loaders | `src/lib/data.ts` (main), `src/lib/humanize.ts` (30+ copy rules) | You are touching copy, charts, or market data |
| React islands | `src/lib/charts/` | You are adding an interactive chart |
| PocketBase realtime | `src/scripts/desk-realtime.ts` | You are wiring live data into a page |
| Pipeline | `watchers/`, `mergers/`, `packagers/`, `distributors/` | You are changing how the desk produces data |
| Pipeline ops | `docs/pipeline-ops.md` | Pipeline won't run / cycles stale |
| Copy rules | `src/lib/humanize.ts` (header) | You are adding or changing copy |

The product is an Astro 7 + React 18 + TanStack Charts 0.11 site. The
production surface is the Astro static build. React powers the TanStack
island on `/build` and the existing HTM map-drill renderer on `/`; keep
new homepage visuals in plain Astro unless an interaction genuinely needs
the established drill runtime.

## Build / test / verify

```bash
pnpm install                                              # one-time
pnpm run build                                            # static + serverless build; must be green
pnpm run test:types                                       # chart/island TypeScript contract
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests --ignore=tests/e2e -q
pnpm run test:e2e                                         # browser suites; auto-starts Astro preview
```

Vercel auto-deploys `main` on push. **Do not push unless the user asks**
(user's standing rule). Local changes ship via PR after manual
`gh pr merge --squash`. Watch the build log after merge. Check Vercel's
current function limit before adding `api/*.py`; the repo's
`.vercelignore` data-endpoint pattern is the established fallback.

## Design system (read before changing colors or copy)

| Token | Value | Used for |
|-------|-------|----------|
| `--bg` / `--ink` / `--card` | warm-paper #F4EBDD / near-black #18251F / off-white #FFFCF4 | Page surface |
| `--gold` / `--teal` / `--sky` / `--coral` | #B57A22 / #0D766E / #2676A8 / #B94836 | Editorial accent palette (also matches caribbeanTheme sea/reef/sand/sun) |
| `--caribbean-*` | see `src/lib/caribbean-theme.ts` | TanStack Charts palette (must stay in sync with `signal-fabric-designer/src/charts/caribbean-theme.ts`) |
| Font | Inter Variable (sans), Cormorant Garamond (serif), IBM Plex Mono (mono) | Inherited from `index.html` <link> preconnect |

**Copy must flow through `humanize()`** (in `src/lib/humanize.ts`). 30+
rules map technical phrase → human. Examples: "WB FDI surge detected: $1"
→ "World Bank sees money moving into $1"; "WB" → "World Bank"; "FDI" →
"foreign investment"; "High-confidence signal" → "Strong signal". If you
add new copy, either extend the rules or add a comment explaining why the
technical term is fine.

## Chart contract

**Two render paths exist for the same data.** Pick the right one:

1. **Astro SVG path** (used on `/` and `/regional-connections`):
   `buildIndexedCandlestickSvg()` in `src/lib/data.ts`. Static,
   deterministic, ships zero JS. Use for static/deterministic charts
   per the design decision recorded in memory.

2. **TanStack Charts React island** (used on `/build`): the
   `LollipopIsland` in `src/lib/charts/LollipopIsland.tsx`.
   Interactive, ships JS. Use for client islands per the design
   decision.

**TanStack chart shape contract:**
- All chart definitions use `defineChart()` from `@tanstack/charts`.
- All chart definitions apply `theme: caribbeanTheme` from
  `src/lib/caribbean-theme.ts`.
- All chart definitions that show data MUST include a `dataAsOf` label
  (freshness rule).
- The data adapter `opportunitiesFromDesk()` in
  `src/lib/charts/lollipop.ts` is the canonical
  `dispatch_desk.json → lollipop` converter. Use it; do not write your own.
- `dataAsOf` must come from the source artifact (`generated_at`, then the
  cycle date as fallback), never from the page build time.

**Anti-patterns (don't do these):**
- Do NOT hardcode hex colors in chart definitions. Use
  `var(--caribbean-*, #fallback)`.
- Do NOT add a new chart on the homepage without porting its theme to
  caribbeanTheme.
- Do NOT bypass `humanize()` for new copy.
- Do NOT install another chart library (Recharts, D3, Chart.js, etc.) —
  the project is intentionally TanStack for islands and Astro SVG for
  static.
- Do NOT edit `src/lib/caribbean-theme.ts` without syncing
  `signal-fabric-designer/src/charts/caribbean-theme.ts`. They must stay
  identical.
- Do NOT run the full `run_pipeline.sh` from a local session — it
  sends Telegram messages. Run individual stages instead (see
  `docs/pipeline-ops.md`).

## Layout & responsiveness

- The homepage `.map-shell` section targets a full-width map hero at
  560–720px desktop.
- `/build` is the configurator page. Sticky left rail (controls) +
  flexible right pane (preview).
- All sections should be readable on a 360px-wide phone.
- Avoid population bubble maps, geo choropleths, generic sparklines on
  every card, fake price charts, visible confidence charts without
  rationale.

## What to update when...

- **Adding a new source or signal** → `config/*_sources.json`, then
  re-run the matching `watchers/*_poller.py` stage.
- **Adding a new persona / channel / domain** → `config/recipients.json`
  + `config/desk_presets.json`. Update `/build` chips too.
- **Adding a new API endpoint** → `api/<name>.py` (BaseHTTPRequestHandler
  pattern). Add a route in `vercel.json` only if not covered by the
  `^/api/([^/]+)$` catch-all. Check the current Vercel plan limit; if
  you hit it, add the new `.py` to `.vercelignore` and serve the data
  as `api/<name>-data.json` instead. See the existing
  `api/market-watch.py` / `api/regional-news.py` / `api/source-health.py`
  pattern in `.vercelignore` for the recipe.
- **Adding a new Astro page** → `src/pages/<name>.astro`; use
  `getStaticPaths` for dynamic routes. Add a section anchor in
  `src/components/home/RegionalPulse.astro` if it's a top-level section.
- **Adding a new pocketBase collection** → extend
  `backend/pocketbase/setup.mjs`. Don't run setup.mjs against a live PB
  without the user present.
- **Adding a new chart** → mirror the lollipop pattern in
  `src/lib/charts/`. Always: server-side data in frontmatter, React
  island in markup, dataAsOf label, caribbeanTheme.

## Astro-specific gotchas

- `<script is:inline>` runs the script in the page body. It CANNOT
  reference frontmatter `const`s — the page is a single HTML doc but
  the frontmatter is server-rendered and inlined separately. Use
  Astro's `define:vars` or pass via `<script type="module">` imports
  instead.
- React islands use `client:load` (interactive) or `client:visible`
  (defer). Static SVG is always preferred for the homepage.
- The build will fail with `XYZ is not defined` if you reference
  frontmatter `const`s inside a `<script is:inline>` block. Move the
  script to a real Astro component.
- `data/*` is `.vercelignore`'d by default. If your serverless
  function reads `data/foo.json`, you must also (a) commit
  `public/foo.json` or `api/foo-data.json` AND (b) add `!data/foo/`
  to `.vercelignore`. See `docs/pipeline-ops.md` and the
  source-health / feedback fallback pattern in `api/status.py`.

## How to verify a change end-to-end

1. `pnpm run build` — must be green.
2. `pnpm run test:types` — must be green.
3. `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests --ignore=tests/e2e -q` — all collected tests must pass; do not hard-code a count here.
4. `pnpm run test:e2e` — required for homepage drill and chart changes; static checks do not catch React runtime failures.
5. After an approved merge, inspect the Vercel deployment and query `/api/status`; do not treat a preview or local artifact as production proof.

If a check fails, do NOT push — fix and re-verify.

## Cross-machine reality check

There is a **separate React+Vite app** at
`/Users/christopherbelgrave/Documents/signal-fabric-designer/` that
defines the *illustrative* chart shapes (populationBubbleMap,
opportunityLollipop) and the caribbeanTheme. It is a chart-design
workbench, not the live site. **The live site is the Astro repo at
`/Users/christopherbelgrave/clawd/projects/future-caribbean/`.**

If the user mentions "the designer" or "the workbench", they're
referring to the React app. If they mention "the site" or "the live
product" or "Abeng", they're referring to the Astro repo.
Same for charts:
- Designer (`/Users/christopherbelgrave/Documents/signal-fabric-designer/`)
  = where chart shapes are designed and demoed
- Astro site (`/Users/christopherbelgrave/clawd/projects/future-caribbean/`)
  = where the same chart shapes are rendered for end users

`src/lib/caribbean-theme.ts` (Astro) and
`/Users/christopherbelgrave/Documents/signal-fabric-designer/src/charts/caribbean-theme.ts`
(designer) are the same file semantically. **They must stay in lockstep.**
If you change one, change the other. The Astro version uses CSS variables
for the live site; the designer version is the canonical hex palette.
The two-way rule is the test `test_caribbean_theme_uses_css_variables_with_fallbacks`
in `tests/test_lollipop_chart.py`.

## The handoff between pipeline and site

```
                    ┌──────────────────────┐
                    │  Pipeline (Python)    │
  public data  ───▶ │  watchers / packagers │ ───┐
                    │  outbox/ + data/      │    │
                    └──────────────────────┘    │
                                              │
                                              ▼
                    ┌──────────────────────┐
                    │  Astro site           │
  committed JSON ─▶  │  src/lib/data.ts      │ ──▶ rendered HTML
  (public/, api/,   │  src/lib/humanize.ts  │
   outbox/)         │  src/lib/charts/      │
                    └──────────────────────┘
```

The pipeline produces deterministic JSON. The site reads it at build time
and renders HTML. **The site never calls the pipeline at runtime.**
This is by design: the Astro static build is fast, indexable, and works
without any backend. If you need live data, the pattern is a PocketBase
React island (see `src/scripts/desk-realtime.ts` for the precedent).
