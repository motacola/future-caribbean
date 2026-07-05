# Astro Migration Handover — Claude Code

## Status: COMPLETE (July 2026)

The migration finished and the legacy surface has been retired. Astro is the single source of truth for the UI.

- `src/pages/index.astro` ✅ full dashboard (all sections: masthead, live wire, map, decision workspace, market watch, theater, ask desk, receipts, for-agents)
- `src/pages/build.astro` ✅ full configurator port
- `src/pages/signal/[id].astro` ✅ signal permalinks
- `src/lib/data.ts` ✅ data layer (port of the old generate.py loaders; reads `outbox/`, `config/`, `data/` at build time)
- `vercel.json` ✅ routes `/` and `/build` to `dist/` (built via `scripts/vercel-build.sh`)
- `server.py` ✅ serves `dist/` locally; `/dashboard.html` and `/configurator.html` now 301-redirect to `/` and `/build`

## Retired (July 2026)

Deleted from the tree (recoverable from git history):
- `dashboard.html` — generated legacy page
- `dashboard/template.html` + `dashboard/generate.py` — legacy generator
- `configurator.html` — static legacy build page

`run_pipeline.sh`'s Dashboard step now runs `pnpm build` (Astro) instead of `generate.py`. Tests that asserted on the legacy files were ported to `dist/index.html` / `src/pages/index.astro` (`tests/test_frontpage.py`, `tests/test_track_record.py`, `tests/test_week2d.py`).

## Operational notes

- Data is baked at build time: new cycle data appears only after `pnpm build` (the pipeline does this as its Dashboard step; Vercel builds on deploy).
- `scripts/vercel-build.sh` also copies `feed.xml`, `llms.txt`, `agents.md`, and `data/history/` into `dist/`.
- Do not modify `watchers/`, `mergers/`, `packagers/`, `api/*.py` for UI concerns — the Python layer only produces JSON; all rendering lives in `src/`.
