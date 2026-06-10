# Caribbean Opportunity Dispatch

**Routed opportunity and risk dispatches from fragmented Caribbean public data — readable by humans, queryable by any AI agent.**

Powered by **Signal Fabric**, a continuous multi-agent pipeline that watches public regional data, merges weak signals across sources, packages them into routed dispatches for specific decision-makers, pre-assembles the diligence evidence, and learns from recipient feedback.

**Track:** 10 — Open Track (Future Caribbean Buildathon)

**Category:** Agentic market coordination infrastructure for fragmented Caribbean economies.

Caribbean Opportunity Dispatch belongs in Open Track because it is not a sector-specific app. Finance, disaster risk, food, ocean, tourism, and procurement are signal domains; the product is the cross-sector routing layer that turns those signals into action — and the first agent-ready opportunity API for the region.

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
| **Humans (browser)** | `dashboard.html` — decision workspace, live map, cycle theater, ask-the-desk |

Discovery files: [`llms.txt`](llms.txt) and [`agents.md`](agents.md) (also served over HTTP) describe every endpoint with copy-paste examples per framework.

Answers are **deterministic and cited** — they come from the generated desk artifacts, not an LLM, so they are free, offline, and never hallucinate in front of a judge.

```bash
# the same engine, three ways
curl -X POST localhost:8080/api/ask -d '{"question":"explain lead"}'
python3 cli/signalctl.py ask "what changed this cycle"
python3 agent/query.py ask "draft Belize investor note"
```

## The Dashboard

`python3 server.py` then open `http://localhost:8080/dashboard.html`:

- **Decision workspace** — the lead signal as a decision, not a headline: recommended move, action window, named owner, evidence grade, diligence checklist, and the full validation pack inline
- **Ask the desk** — chat panel wired to the deterministic query engine, with citations
- **Live Caribbean map** — 13 watched countries, signal pulses sized by confidence, click to drill
- **Cycle theater** — watch the pipeline run live over SSE (sources lighting up, signals forming, dispatches routing), with a replay mode that works without network from `data/history/`

## Architecture (Signal Fabric)

```
public data -> watchers -> normalized records -> reasoning merger -> composite signals
                                                                  -> opportunity dispatches (the product)
                                                                  -> validation packs (auto-diligence)
                                                                  -> regional thesis + why-now context
                                                                  -> feedback loop (re-weights next cycle)
                                                                  -> agent interface (HTTP / MCP / CLI)
                                                                  -> decision workspace (dashboard.html)
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
| `dashboard.html` | The decision workspace (regenerated each cycle) |

## Data Sources

All sources are public, free, and require no API keys:

| Source | Method | Data |
|---|---|---|
| **World Bank** | REST API | 5 indicators × 13 Caribbean countries |
| **IDB Open Data** | CKAN API | 99 Caribbean datasets |
| **NOAA NWS** | REST API | Active weather alerts |
| **NDBC Buoys** | Tabular text | 6 buoys: wind, pressure, wave height |
| **CARICOM Statistics** | WordPress REST API | 126 datasets |
| **CDB** | RSS feed | Procurement notices, evaluation reports |

## Run

```bash
# full pipeline (watchers -> merger -> packagers -> validation packs -> dashboard)
bash run_pipeline.sh

# serve the dashboard + API (also auto-runs the pipeline every 4h)
python3 server.py            # http://localhost:8080/dashboard.html

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

```bash
npm run flue:apply-feedback
npm run flue:prepare-delivery -- '{"channel":"telegram"}'
npm run flue:approve-delivery -- '{"approvalId":"APP-...","approvedBy":"operator"}'
npm run flue:send-approved -- '{"approvalId":"APP-...","dryRun":true}'
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

## Deployment

### Vercel + GitHub Actions (recommended, $0 hosting)

This is the primary public deployment: GitHub Actions runs the pipeline every 4 hours and commits artifacts; Vercel serves `dashboard.html` + static artifacts plus Python serverless functions for the read-only APIs.

**Live URL:** `https://<project>.vercel.app` (replace after first deploy)

**Setup (3 steps):**

1. **Import repo in Vercel**
   - New Project → Import this GitHub repository
   - Framework Preset: **Other**
   - Root Directory: `/` (repo root)
   - No build command, no output directory needed (static + functions)
   - Deploy — Vercel detects `vercel.json` and `api/` functions automatically

2. **Enable the GitHub Actions workflow**
   - The `.github/workflows/pipeline.yml` runs on a 4-hour cron + manual dispatch
   - Add optional secrets for Telegram delivery (not required for read-only API):
     - `TELEGRAM_BOT_TOKEN`
     - `TELEGRAM_CHAT_ID`
   - Workflow commits artifacts → auto-triggers Vercel redeploy

3. **Done** — open the Vercel URL. The dashboard, map, theater replay, and `/api/ask`, `/api/status`, `/api/validation-packs`, `/api/map-data`, `/api/tools.json` all work.

**Notes:**
- Write endpoints (`/api/feedback/apply`, `/api/delivery/*`, `/api/domains/create`) are **not deployed** — public instance is read-only by construction
- Theater uses client-side replay from committed `data/history/*.jsonl` (no SSE on Vercel)
- Local development unchanged: `python3 server.py` for full read-write + live SSE

---

### Static hosting (Netlify, GitHub Pages, etc.)

For pure static hosting without API functions:

1. Run `bash run_pipeline.sh` to generate all artifacts
2. Deploy `dashboard.html`, `outbox/*.md`, and `assets/` as static files (the dashboard degrades gracefully without the API)
3. No build step needed — all HTML/Markdown is self-contained
4. Cron jobs on the backend continue data collection independently
