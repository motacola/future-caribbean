# Abeng architecture

Companion explanation for the interactive Archify map:

- [`abeng-system-map.html`](./abeng-system-map.html) — self-contained interactive diagram
- [`abeng-decision-lifecycle.html`](./abeng-decision-lifecycle.html) — decision and outcome lifecycle
- [`abeng-operations.html`](./abeng-operations.html) — operations, publication, and delivery
- [`abeng-intervention-lifecycle.html`](./abeng-intervention-lifecycle.html) — the enforced
  intervention state machine (Archify `lifecycle` mode, so its citations are text in the cards rather
  than machine-verified repository evidence, which is architecture-only)
- [`abeng-system-map.compact.architecture.json`](./abeng-system-map.compact.architecture.json) — verifiable architecture source

All four HTML diagrams were rendered from their JSON sources on 2026-09-04 at Archify showcase
quality: 9/9 artifact checks, 0 composition errors, 0 warnings, and 16 visual-check captures each
across four viewports in both themes. Evidence links are pinned to `4a26fb3`. **Re-render after any
edit to a JSON source** — the HTML is a build output, not a hand-maintained file.

## What Abeng is

Abeng is a deterministic coordination engine for fragmented markets. The Caribbean instance watches public regional evidence, converts weak signals into cited opportunity products, routes them to the right personas, assembles diligence and coordination context, and learns from explicit recipient outcomes.

The system is file-centred rather than database-centred. Pipeline stages exchange JSON, Markdown, CSV, XML, and HTML artifacts. That makes every decision inspectable and lets the website, HTTP API, MCP adapter, CLI, RSS feed, and message packets share one canonical evidence layer.

## End-to-end flow

1. **Acquire public evidence.** Pollers under `watchers/` collect economy, procurement, climate, and news data. `run_pipeline.sh:60-82` runs these stages with cache/fallback behavior.
2. **Preserve state and freshness.** Source snapshots, histories, health ledgers, feedback, calibration, and registry files live under `data/`. This state is committed by the scheduled GitHub Actions workflow so the next cycle has memory.
3. **Correlate weak signals.** `mergers/cross_source_merger.py` performs deterministic fact identity, source provenance, freshness handling, and cross-source correlation. Its output is the composite signal layer, not a free-form model response.
4. **Rank and package decisions.** The packagers convert composite signals into persona routes, evidence bars, validation packs, and dispatch clusters. Feedback-adjusted priority is applied here, with raw and adjusted confidence kept distinct.
5. **Resolve coordination gaps.** `coordination/engine.py` matches demand against cited capability entries, identifies blockers and owners, and emits intervention or unlock paths. It does not silently invent missing capabilities.
6. **Optionally synthesize a narrative.** `reasoners/synthesis.py` runs inside the
   cycle (`run_pipeline.sh:119`). It reads the desk artifacts and writes
   `outbox/reasoning.json`. If `LLM_BASE_URL`/`LLM_API_KEY` are configured the thesis
   is model-generated; otherwise a deterministic synthesizer produces it. Either way the
   payload records which engine ran, and that label travels with the artifact. This is the
   one place model output enters the published surface — see Trust model below.
7. **Publish canonical artifacts.** `outbox/` holds the dispatch desk, validation packs, feeds, track record, and delivery packets. This is the shared contract between pipeline generation and delivery.
8. **Serve humans and agents.** Astro reads the artifacts at build time for the editorial desk. Vercel Python functions expose request-time JSON endpoints. The MCP adapter and `abengctl` CLI query the same local contracts; RSS and channel packets reuse the same outputs.
9. **Learn from outcomes.** Explicit outcomes enter the feedback ledger, decay over time, and become bounded priority boosts in later cycles. Read paths remain public; hosted writes are authenticated or disabled unless correctly configured.

## Application boundaries

### Pipeline engine

Owned by `watchers/`, `mergers/`, `reasoners/`, `coordination/`, `packagers/`, `domains/`, and `run_pipeline.sh`. It owns acquisition, normalization, correlation, ranking, validation, coordination, and artifact generation.

### Canonical artifact boundary

Owned by `data/`, `outbox/`, `packets/`, and generated public files. These files are both state and interface contracts. Their citations and cycle metadata are the audit trail.

### Product delivery boundary

Owned by `src/`, `api/`, `api_manifest.py`, `mcp_adapter/`, and `cli/`. These layers present existing artifacts; they should not independently reinterpret or regenerate opportunity evidence.

### Operations and deployment boundary

`.github/workflows/pipeline.yml` runs the scheduled/on-demand data refresh: it executes
`run_pipeline.sh` and commits a filtered set of artifact paths. It does not invoke
`scripts/verify.sh` — that gate (build, pytest, ranking, ledger chain, browser tests) is run
by an operator before a release, and it restores four tracked artifacts on exit, so it cannot
be dropped into the cycle between the run and the commit without reverting fresh data. `scripts/vercel-build.sh` prepares generated website assets and then runs the Astro production build. `vercel.json` maps Python API functions and static routes on the deployed Vercel project.

## Frontend behavior

`src/lib/data.ts` is the build-time adapter between the artifact layer and typed view models. `src/pages/index.astro` renders the editorial desk, map, market-watch panels, evidence language, and browser interactions. Client-side state handles presentation such as country drills, lenses, follows, tabs, and local progress; the opportunity evidence itself comes from generated artifacts.

This distinction matters: the frontend is a delivery and exploration layer, not the signal-detection engine.

## Backend and API paths

`api_manifest.py` defines the shared HTTP tool manifest and route handlers. Thin Vercel functions delegate to it. `/api/ask` calls `agent/query.py`, which answers from generated desk artifacts and appends file citations. The MCP server and CLI expose equivalent local operations, avoiding SDK lock-in.

## Build and deployment flow

- **Data cycle:** GitHub Actions or an operator runs `run_pipeline.sh`; essential-step failures
  stop the run before publication; generated state and product artifacts are committed.
- **Web build:** Vercel executes `scripts/vercel-build.sh`; build-time adapters read the committed artifacts; Astro emits the static site.
- **Runtime:** static pages serve the desk while Python functions read committed artifacts for API requests.
- **Failure path:** optional watcher failures retain stale cached data and expose freshness/health
  instead of presenting stale evidence as fresh (`run_pipeline.sh:12-26`). A failure in an
  essential step exits non-zero and refuses to publish (`run_pipeline.sh:173-183`).

## Trust model

- Ranking, routing, freshness, query answers, and citations are deterministic and inspectable.
- Evidence lineage stays attached to source files and URLs.
- Confidence changes are bounded and preserve raw versus adjusted values.
- Optional synthesis is confined to `outbox/reasoning.json`. It is served at
  `/api/reasoning` and rendered on the homepage (`src/pages/index.astro:2978`), and the
  payload always names the engine that produced it. No other artifact, ranking, routing,
  or citation depends on it, and the public `/api/ask` path is deterministic over
  generated artifacts.
- The local operator server authenticates mutations, and the two reads that expose
  operator state rather than product — `/api/delivery/approvals` and `/api/webhooks` —
  now require the same token. Requests are also rejected when the bind address is
  loopback and the `Host` header is neither loopback nor a configured origin, which is
  what stops a page resolving its own domain to `127.0.0.1`. Every other GET keeps
  `Access-Control-Allow-Origin: *`; those are published surfaces.
- Hosted write paths require authentication; read paths are the default public surface.
- Delivery approvals carry five states — `pending`, `approved`, `sent`, `dry-run-sent`, `rejected`
  (`.flue/tools/delivery.ts:20`). The operations diagram states the count rather than a partial list.

## Primary code evidence

| Concern | Evidence |
|---|---|
| Pipeline orchestration | `run_pipeline.sh:60-164` |
| Scheduled refresh and selective commit | `.github/workflows/pipeline.yml:28-97` |
| Manual release gate (no automated caller) | `scripts/verify.sh:1-61` |
| Composite signal contract | `mergers/cross_source_merger.py:44-69` |
| Dispatch ranking | `packagers/dispatch_desk.py:121-190` |
| Feedback state and decay | `packagers/feedback_loop.py:27-31`, `packagers/feedback_loop.py:105-161` |
| Coordination rules | `coordination/engine.py:16-31`, `coordination/engine.py:95-141` |
| Build-time frontend adapter | `src/lib/data.ts:510-560` |
| Homepage composition | `src/pages/index.astro:1-200` |
| HTTP surface | `api_manifest.py:3-204`, `api/ask.py:17-74` |
| Deterministic Q&A | `agent/query.py:1-80` |
| Optional synthesis and its engine label | `reasoners/synthesis.py:9-22`, `reasoners/synthesis.py:205-236` |
| Synthesis public surface | `api/reasoning.py:1-27`, `src/pages/index.astro:2978` |
| Operator-server trust boundary | `server.py:28-30`, `server.py:306-341`, `tests/test_server_security.py` |
| MCP and CLI adapters | `mcp_adapter/desk_server.py:36-49`, `cli/abengctl.py:1-27` |
| Vercel build and routing | `scripts/vercel-build.sh:10-31`, `vercel.json:1-76` |
