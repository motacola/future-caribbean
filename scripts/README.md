# scripts/

Deterministic checks. Each of these replaces work that was previously done by
an agent writing a throwaway snippet inline and reading its output — which is
where the tokens went. **Run these instead of rewriting them.**

| Script | Replaces | Cost |
|---|---|---|
| `./scripts/verify.sh` | build + pytest + ranking + ledger chain + e2e, retyped each time | 0 tokens |
| `./scripts/verify.sh fast` | same, without the browser tests (~20s) | 0 tokens |
| `python3 scripts/verify_ranking.py` | hand-checking lead order, score separation, order-independence | 0 tokens |
| `node scripts/shot.mjs OUT.png [--sel S] [--mobile] [--url U]` | ad-hoc Playwright capture snippets | 0 tokens |

## Notes

**`verify.sh` restores tracked artefacts afterwards.** The existing test suite
rewrites `outbox/track_record.json`, `api/feedback-data.json`,
`data/coordination/graph.json` and `outbox/coordination_opportunities.json`.
Until that is fixed, a verification run must not change what the site
publishes. Fixing those tests is the single biggest remaining saving — it is
what forced repeated re-checking in the first place.

**Use `node ./node_modules/astro/bin/astro.mjs build`, not `pnpm build`.**
`pnpm build` triggers `pnpm install`, which aborts without a TTY and wants to
purge `node_modules`.

**`shot.mjs` ignores four expected 404s.** `/api/map-data`, `/api/domains`,
`/api/reasoning` and `/api/status` are Vercel Python functions; `astro preview`
serves the static build only, so they 404 locally by design and the page guards
each one. Genuine errors still fail the run with a non-zero exit.

## The pipeline itself is already token-free

`run_pipeline.sh` makes **one** LLM call, in `reasoners/synthesis.py`, and it
already falls back to a deterministic synthesiser — which is the engine
currently in use. The output records which engine produced it. The 4-hourly
cycle costs nothing in tokens; do not add an LLM call to it without a reason
that survives §4 of the handover.
