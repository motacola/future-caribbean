# Astro Migration Handover — Claude Code

## Goal
Migrate Signal Fabric's public product surface from generated Python HTML to Astro, while keeping the Python intelligence layer and `/api/*` endpoints untouched.

## Verified Progress
- `astro.config.mjs` exists and `pnpm build` passes
- `src/lib/humanize.ts` ✅ complete
- `src/lib/data.ts` ✅ complete (~743 lines)
- `src/layouts/Base.astro` ✅ complete
- `src/pages/index.astro` ⚠️ still a 31-line fetch stub; full dashboard port pending
- `src/pages/build.astro` ⚠️ placeholder; configurator port pending
- `vercel.json` ❌ not yet updated for Astro output
- `ASTRO_MIGRATION_HANDOVER.md` ❌ out of date; this file replaces it

## State Reference
A detailed migration state file exists at `misc/astro-migration-state.md` (or equivalent) with:
- field names
- mapping rules
- `<Fragment set:html>` data injection pattern
- `<script is:inline>` block details
- lines 1341 and 1516 skip notes

Use that file as the source of truth for writing `index.astro` without re-reading all dashboard source files.

## What to Do Next (in order)
1. **`src/pages/index.astro`** — full port of `dashboard/template.html`
   - Split writes by section: CSS block, HTML body, scripts+footer
   - Do not attempt one monolithic write; the file is ~1700 lines
   - Keep all Python endpoints intact as data sources
2. **`src/pages/build.astro`** — port of `configurator.html`
   - Change one link: `/dashboard.html` → `/`
3. **`vercel.json`** — add `dist/**` static build and update routes:
   - `/` → `/dist/index.html`
   - `/build` → `/dist/build/index.html`
   - `/(.*)` → `/dist/(.*)`
4. **`pnpm build`** — verify build succeeds with real data
5. **Update this handover** to reflect completion

## Hard Boundaries
- Do not modify `watchers/`, `mergers/`, `packagers/`, `api/*.py`, `server.py`, `run_pipeline.sh`
- Do not delete `dashboard.html` or `dashboard/template.html` until Astro is validated end-to-end
- Preserve product-first language rules from `signal-fabric-development` skill

## Known Pitfalls
- Claude Code previously hit the 32k token output cap when writing `index.astro` in one shot
- Pi timed out on large page-generation prompts; prefer incremental file writes
- Vercel still serves `dashboard.html` at `/` — Astro output is not yet live

## Files of Interest
- `dashboard/template.html`
- `dashboard/generate.py`
- `configurator.html`
- `vercel.json`
- `package.json`
- `src/pages/index.astro`
- `src/pages/build.astro`
- `src/layouts/Base.astro`
- `src/lib/data.ts`
- `src/lib/humanize.ts`
- `api/*.py`
