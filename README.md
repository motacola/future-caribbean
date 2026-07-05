# Signal Fabric

Signal Fabric is an agentic coordination infrastructure for fragmented economies: it watches public regional data, merges weak signals, routes opportunity dispatches to the right personas with auto-assembled diligence packs, and learns from recipient feedback. The Caribbean is the live proof; the engine is domain-agnostic (economic + climate instances today). Any agent can query it via HTTP, MCP, or CLI — it's deterministic, cited, and deployable now.

---

**Routed opportunity and risk dispatches from fragmented Caribbean public data — readable by humans, queryable by any AI agent.**

Powered by **Signal Fabric**, a continuous multi-agent pipeline that watches public regional data, merges weak signals across sources, packages them into routed dispatches for specific decision-makers, pre-assembles the diligence evidence, and learns from recipient feedback.

**Track:** 10 — Open Track (Future Caribbean Buildathon)

**Category:** Agentic market coordination infrastructure for fragmented Caribbean economies.

Signal Fabric belongs in Open Track because it is not a sector-specific app. Finance, disaster risk, food, ocean, tourism, and procurement are signal domains; the product is the cross-sector routing layer that turns those signals into action — and the first agent-ready opportunity API for the region.

---

## The Problem

Caribbean opportunity data is scattered across institutions, countries, and formats. That fragmentation delays investment decisions, procurement responses, resilience planning, founder matching, and public narrative.

Existing tools stop short:
- Data portals expose datasets but do not route decisions
- Newsletters explain market context but do not run a repeatable signal pipeline
- Dashboards show status but do not package channel-ready action
- Investor catalogues list opportunities but are not continuous watchers
- Nothing in the region is queryable by AI agents

This fills the **last mile between public regional data and acted-on opportunity**. The goal is to compress the time between public signal and economic action.

## The Product

Each 4-hour cycle converts raw public data into:

- **Priority** — what matters this cycle, evidence-graded
- **Routing** — who should receive it (persona + channel)
- **Action** — what decision it should trigger, with an action window
- **Validation** — an auto-assembled diligence pack per lead signal: sector hypotheses, supporting projects, procurement matches, intro targets, and an explicit advance/hold/reject recommendation with reasons
- **Learning** — whether the dispatch produced a real response (feedback loop re-weights future cycles)
- **Distribution** — channel-ready packets with an approval-gated delivery manifest

The useful artifact is the dispatch, not the chart.

## Works With Any Agent

The engine is agent-agnostic by design. The contract is a plain HTTP API plus a machine-readable tool manifest — MCP is one adapter on top, not the foundation.

| Client | How it connects |
|---|---|
| **Any agent / curl** | `GET /api/tools.json` — self-describing tool manifest; `POST /api/ask` for cited answers |
| **Claude (Code/Desktop)** | MCP adapter: `mcp_adapter/desk_server.py` (see `mcp_adapter/README.md`) |
| **Hermes / OpenClaw** | Point HTTP tooling at `/api/tools.json`, or shell out to `cli/signalctl.py` |
| **Flue** | Workflow harness in `.flue/` (`ask-dispatch`, `run-cycle`, `record-feedback`, …) |
| **Humans (terminal)** | `python3 cli/signalctl.py status\|signals\|preview\|ask\|reason\|send` |
| **Humans (browser)** | Astro site (`/`) — decision workspace, live map, cycle theater, ask-the-desk |

Discovery files: [`llms.txt`](llms.txt) and [`agents.md`](agents.md) (also served over HTTP) describe every endpoint with copy-paste examples per framework.

Answers are **deterministic and cited** — they come from the generated desk artifacts, not an LLM, so they are free, offline, and never hallucinate in front of a judge.

```bash
# the same engine, three ways
curl -X POST localhost:8080/api/ask -d '{"question":"explain lead"}'
python3 cli/signalctl.py ask "what changed this cycle"
python3 agent/query.py ask "draft Belize investor note"
```

## The Dashboard

Run `pnpm build` for the Astro static frontend, or `python3 server.py` and open `http://localhost:8080/`:

- **Decision workspace** — the lead signal as a decision, not a headline: recommended move, action window, named owner, evidence grade, diligence checklist, and the full validation pack inline
- **Ask the desk** — chat panel wired to the deterministic query engine, with citations
- **Live Caribbean map** — 23 watched Caribbean markets and territories, signal pulses sized by confidence, click to drill; every beacon has either a routed live signal or a clearly labeled market/FX watchlist signal
- **Cycle theater** — watch the pipeline run live over SSE (sources lighting up, signals forming, dispatches routing), with replay fallbacks from `data/history/` and an embedded recorded-cycle event stream for production/static deploys

## Architecture (Signal Fabric)

```
public data -> watchers -> normalized records -> reasoning merger -> composite signals
                                                                  -> opportunity dispatches (the product)
                                                                  -> validation packs (auto-diligence)
                                                                  -> regional thesis + why-now context
                                                                  -> feedback loop (re-weights next cycle)
                                                                  -> agent interface (HTTP / MCP / CLI)
                                                                  -> decision workspace (Astro site, dist/)
```

## Key Artifacts (outbox/)

| Artifact | What it is |
|---|---|
| `outbox/dispatch_desk.md` | Primary product surface: grouped decision clusters with persona routes, evidence, action, and feedback |
| `outbox/opportunity_dispatches.md` | Canonical routed dispatches with persona, channel, action, and feedback status |
| `outbox/validation_packs/*.{json,md}` | Auto-assembled diligence pack per lead signal with advance/hold/reject recommendation |
| `outbox/regional_thesis.md` | Cross-cluster synthesis — investment, risk, pipeline, tourism in one narrative |
| `outbox/why_now.md` | Editorial calendar context — seasonal windows, procurement cycles, etc. |
| `outbox/judge_brief.md` | Full system intelligence brief with routing rationale |
| `outbox/feedback_review.md` | Feedback loop — what was forwarded, replied to, opened, or changed a decision |
| `outbox/dispatch_packets/*.md` | Persona-specific dispatch packets (action checklists, evidence, feedback options) |
| `outbox/delivery_manifest.json` | Channel-ready delivery manifest (one entry per dispatch) |
| `dist/index.html` | The decision workspace (Astro build, refreshed each cycle) |

## Data Sources

All sources are public, free, and require no API keys:

| Source | Method | Data |
|---|---|---|
| **World Bank** | REST API | 5 indicators × watched Caribbean countries |
| **IDB Open Data** | CKAN API | 99 Caribbean datasets |
| **NOAA NWS** | REST API | Active weather alerts |
| **NDBC Buoys** | Tabular text | 6 buoys: wind, pressure, wave height |
| **CARICOM Statistics** | WordPress REST API | 126 datasets |
| **CDB** | RSS feed | Procurement notices, evaluation reports |
| **CCRIF SPC** | Web scraping | Parametric insurance payouts (tropical cyclone, earthquake, excess rainfall) |
| **ECCB** | Web scraping | Monetary & financial stats (private credit, deposits, NFA, total assets) |

## Signal Types (Composite Rules)

| Signal | Priority | Sources | Description |
|---|---|---|---|
| 🌀 Cyclone Risk | High | NDBC + NOAA | Buoy pressure drop + marine advisory |
| 🚢 Maritime Hazard | Medium | NDBC + NOAA | High wind + marine alert |
| 💼 Investment Signal | Medium | WB + IDB | FDI surge + IDB project match |
| 💎 Enhanced Investment | Medium | WB + CARICOM + CDB | Triple-source FDI validation |
| ⚠️ Economic Vulnerability | Medium | WB | High inflation + unemployment |
| 🏖️ Tourism Impact | Low | WB + NOAA | GDP growth + no wind advisory |
| 🌾 Food Security | Medium | CARICOM + WB | Food trade datasets + inflation cross-ref |
| 🏗️ Development Pipeline | Medium | CDB + IDB | Active procurement + infra projects |
| 🔗 Supply Chain Opportunity | Medium | CDB + NDBC + CARICOM | Procurement + stable maritime + logistics data |
| 💰 CCRIF Parametric Payout | High | CCRIF | Insurance payout ≥$1M = verified hazard + capital |
| 🏦 ECCB Credit Surge | Medium | ECCB | Private credit + deposits + NFA growth |
| 🏦 ECCB Deposit Growth | Medium | ECCB | Deposit base expansion = stability signal |
| 🌪️ Tropical Development | High | NHC + NOAA | High-probability cyclone formation |
| 🌀 Active Storm | High | NHC | Named storm with track data |

## Run

```bash
# full pipeline (watchers -> merger -> packagers -> validation packs -> dashboard)
bash run_pipeline.sh

# serve the dashboard + API (also auto-runs the pipeline every 4h)
python3 server.py            # http://localhost:8080/

# terminal control
python3 cli/signalctl.py status
python3 cli/signalctl.py ask "explain lead"
python3 cli/signalctl.py preview --persona investor --channel telegram

# tests
python3 -m pytest -q
```

### HTTP API (server.py)

Read: `GET /api/status` · `/api/tools.json` · `/api/domains` · `/api/reasoning` · `/api/validation-packs[/<signal_id>]` · `/api/map-data` · `/api/history` · `/api/pipeline/stream` (SSE, `?replay=1` for offline replay) · `/llms.txt` · `/agents.md`

Ask: `POST /api/ask` `{"question": "..."}` → `{answer, citations}`

Write (approval-gated): `POST /api/feedback/apply` · `/api/delivery/prepare` · `/api/delivery/approve` · `/api/delivery/send-approved` (dry-run by default) · `/api/history/archive`

Delivery is intentionally approval-gated: prepare first, approve explicitly, then send. Live Telegram sends require `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`; dry-run is the default.

### Flue harness

`FLUE_MODEL` is required — set it to any model your provider supports before starting:

```bash
export FLUE_MODEL=anthropic/claude-sonnet-4-6   # or openai/gpt-4o, etc.
pnpm flue:dev                                    # start the Flue server
pnpm flue:build                                  # production build → dist-flue/
```

Run workflows directly via CLI:

```bash
pnpm flue:run-cycle
pnpm flue:apply-feedback
pnpm flue:prepare-delivery -- '{"channel":"telegram"}'
pnpm flue:approve-delivery -- '{"approvalId":"APP-...","approvedBy":"operator"}'
pnpm flue:send-approved -- '{"approvalId":"APP-...","dryRun":true}'
```

## Validation Packs — from "investigate" to "here's the evidence"

The biggest gap in regional intelligence products is that they tell you *what* to investigate. Each cycle this system runs the first pass for you. Example (Guyana FDI surge):

- **Sector hypotheses** with explicit bases (analyst priors flagged as unconfirmed; official GDP-by-industry data cited when it exists)
- **Supporting projects** matched from IDB/CDB by country
- **Procurement matches** tagged country vs regional
- **Intro targets** — real public institutions (GO-Invest, JAMPRO, InvesTT, …), never fabricated operators
- **Advance / hold / reject** with the reason stated
- **Unresolved questions** — exactly what a human still has to check this week

## Project Direction

Current build plan: `PLAN_ENGINE_2026-06-10.md`. Implementation briefs and results live in `planning/`. Execution model: strategy and review by Claude, implementation by Hermes, engine pluggable by anything.

---

## Astro build architecture

The frontend is an Astro v7 static build (migrated from a generated `dashboard.html` in June 2026; the legacy generator and HTML files were deleted in July 2026). `pnpm build` outputs to `dist/`, which both `server.py` and Vercel serve.

### Frontend file map

| File | Role |
|---|---|
| `src/pages/index.astro` | Main site — map, briefing, ask-the-desk, all desks |
| `src/pages/signal/[id].astro` | Signal permalink pages (`/signal/DSP-YYYYMMDD-NNN`) |
| `src/pages/build/index.astro` | "Build your feed" configurator page |
| `src/lib/data.ts` | All data loading and HTML template functions |
| `src/lib/humanize.ts` | Label and grade humanization helpers |
| `src/styles/global.css` | Shared CSS |
| `src/layouts/Base.astro` | Base HTML layout with `<head>` slot |
| `astro.config.mjs` | Astro config — `output: "static"`, `outDir: "dist"` |
| `scripts/vercel-build.sh` | Conditional build script (handles dual-project routing) |
| `scripts/future-caribbean-holding.html` | Self-contained holding page for `future-caribbean.vercel.app` |
| `fallow.json` | Fallow dead-code gate — suppresses false positives on Astro deps |

### `server.py` routing

Serves from `dist/` for all Astro output; retired legacy URLs redirect:

```python
if clean.startswith("_astro/"):        → /dist/_astro/...         (Astro hashed assets)
elif clean.startswith("signal/"):      → /dist/signal/<id>/index.html
elif clean in ("", "index.html", ...): → /dist/index.html
elif clean in ("build", "build.html"): → /dist/build/index.html
elif clean == "dashboard.html":        → 301 /        (legacy URL)
elif clean == "configurator.html":     → 301 /build   (legacy URL)
```

### Two Vercel projects, one repo

The repo (`motacola/future-caribbean`) drives two separate Vercel projects:

| Project | URL | What it serves |
|---|---|---|
| `signal-fabric` | `signal-fabric.vercel.app` | **Live production site** — full Astro build |
| `future-caribbean` | `future-caribbean.vercel.app` | **Holding page** — styled 404 until hackathon reveal |

`scripts/vercel-build.sh` reads the `VERCEL_PROJECT_NAME` env var Vercel injects at build time:

```bash
if [ "$VERCEL_PROJECT_NAME" = "future-caribbean" ]; then
  cp scripts/future-caribbean-holding.html dist/index.html
else
  pnpm install && pnpm build   # full Astro build
fi
```

> **Do not add a `builds` array to `vercel.json`.** The legacy `builds` format silently ignores `buildCommand` and reads from git source — deployments will break with no error message. Use `buildCommand` + `outputDirectory` only.

### Vercel route order

Routes in `vercel.json` are evaluated top-to-bottom. The working order:

```
API-specific routes first → /api/tools.json, /api/validation-packs/(.+), /api/community-brief/(.+)
Generic API catchall      → /api/([^/]+)
Named static routes       → /build → /build/index.html, / → /index.html
Signal permalinks         → /signal/(.*) → /signal/$1/index.html   ← must be explicit
Catchall                  → /(.*) → /$1
```

The `/signal/(.*) → /signal/$1/index.html` route cannot be removed. The generic catchall resolves to a directory path, not the `index.html` inside it — Astro puts each signal page at `dist/signal/DSP-xxx/index.html`.

### Signal permalink IDs

IDs follow the pattern `DSP-YYYYMMDD-NNN` and are generated fresh each pipeline cycle. Old IDs 404 cleanly after the next run — no redirect or tombstone. This is intentional; no persistence strategy exists yet.

### Local development

```bash
pnpm install && pnpm build   # build Astro → dist/
python3 server.py            # http://localhost:8080/ — full stack (API + static)
pnpm dev                     # http://localhost:4321/ — HMR only, no /api proxy
```

`dist/` is gitignored. Vercel builds it remotely. `pnpm dev` does not proxy `/api/*` to `server.py` — for full-stack testing use `pnpm build && python3 server.py`.

> **If a Vercel deployment shows stale output after a push**, run `vercel deploy --prod --force` to bust the build cache. Normal git-push redeploys can serve stale static assets even after route changes.

### Leaflet CDN note

Leaflet is loaded via CDN `<script>` and `<link>` tags. Do **not** add `integrity` attributes to these tags — browsers silently block the load if the SRI hash doesn't match, with no console error that identifies the root cause.

### Legacy UI retired (July 2026)

`dashboard.html`, `dashboard/generate.py`, `dashboard/template.html`, and `configurator.html` were deleted — the Astro build is the only UI. The pipeline's Dashboard step now runs `pnpm build`, and `/dashboard.html` / `/configurator.html` 301-redirect to `/` and `/build`. The old files remain in git history if reference is ever needed.

---

## Deployment

### Vercel (current setup)

**Live site:** `https://signal-fabric.vercel.app`
**Holding page:** `https://future-caribbean.vercel.app`

Both projects connect to `motacola/future-caribbean` on GitHub. Push to `main` triggers both. The build script routes each to the right output. API functions in `api/*.py` deploy alongside the static site automatically — public instance is read-only.

**If a deployment looks stale:** `vercel deploy --prod --force` from repo root.

**GitHub Actions** (`.github/workflows/pipeline.yml`) runs the pipeline on a 4-hour cron, commits fresh artifacts, and triggers a Vercel redeploy. Signal IDs rotate with each cycle commit.

```bash
# local: full stack
python3 server.py

# local: frontend HMR only (no API)
pnpm dev

# force-push to Vercel (bypasses build cache)
vercel deploy --prod --force
```

### Static hosting (Netlify, GitHub Pages, etc.)

1. Run `bash run_pipeline.sh` then `pnpm build`
2. Deploy the `dist/` directory
3. Map, briefing, and signal pages work without the API; ask-the-desk and SSE pipeline stream require the Python API layer
