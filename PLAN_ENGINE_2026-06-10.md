# Plan: Newsletter → Caribbean Opportunity Engine

Date: 2026-06-10
Status: APPROVED with decisions (see Decisions section) — 2026-06-10

## Decisions (locked 2026-06-10)

1. **Timeline: 2–3 weeks.** Scope = Phases 1 + 2 fully, plus 3A tender
   watchers. Phase 3B/3C if time allows; Phase 4 only the judge kit (4C).
2. **Demo environment: both.** Local laptop is the primary (replay mode,
   stdio MCP); hosted public URL is the wow-factor backup. Adds workstream
   5 (hosting) — public instance is READ-ONLY (no send/approve/feedback
   writes exposed unauthenticated).
3. **Ask mode: deterministic.** The existing query engine is the demo story:
   free, offline, cited, zero hallucination risk. Framed as a feature.
4. **Branding: dual.** "Caribbean Opportunity Dispatch — powered by Signal
   Fabric" everywhere: product story for judges, platform story for depth.
5. **Agent-agnostic (locked 2026-06-10).** The engine must plug into ANY
   agent — Claude, Hermes, OpenClaw, or anything HTTP-capable. The primary
   contract is the plain HTTP API + a machine-readable tool manifest
   (`/api/tools.json`); MCP is one adapter on top, not the foundation.
6. **Build executor: Hermes.** Hermes implements from build briefs in
   `planning/` (established convention, see `hermes-phase5-action-proof-brief.md`).
   Claude does strategy passes, briefs, and review — not line-by-line build.

## North star

Reposition from "intelligent newsletter" to **the Caribbean's first agent-ready
opportunity engine**: a system that humans read, agents query, and other
software builds on. The winning sentence for a judge:

> "Every other Caribbean intelligence product is a PDF. This one is an API,
> an MCP server, a CLI, and a live desk — and it learns from responses."

Three value claims, each must be demo-provable in under 60 seconds:

1. **Coordination** — watches 13 fragmented markets nobody aggregates because
   each is individually too small. Smallness is the moat.
2. **Machine-readability** — evidence-graded opportunity data any AI agent can
   query natively (MCP). Verifiable "first" in the region.
3. **Learning loop** — recipient responses re-weight future dispatches.

## What already exists (do not rebuild)

| Layer | Asset | State |
|---|---|---|
| CLI | `cli/signalctl.py` — status/domains/signals/preview/reason/run/send | Working |
| HTTP API | `server.py` — status, domains, reasoning, feedback, delivery approvals, SSE pipeline stream | Working |
| Agent harness | `.flue/` — `dispatch-desk` agent + 11 workflows incl. `ask-dispatch` | Working |
| Query engine | `agent/query.py` — 6 deterministic cited intents | Working, **not exposed via API or UI** |
| Validation packs | `packagers/validation_pack_generator.py` + dashboard section | Built 2026-06-10 |
| Multi-domain | `domains/registry.py`, configurator/builder front door | Working |

---

## Phase 1 — Agent-Agnostic Interface Layer (the "first in the Caribbean" claim)

Design rule: **HTTP API is the foundation; every agent framework is an
adapter.** Claude connects via MCP, Hermes via its toolsets/HTTP tools,
OpenClaw via HTTP or the CLI — all hitting the same deterministic engine.

### 1B (build first). Core agent endpoints in `server.py`
- `POST /api/ask` `{question}` → `agent/query.py::ask()` → `{answer, citations}`
- `GET /api/validation-packs` → index of packs
- `GET /api/validation-packs/<signal_id>` → full pack JSON
All read-only, stdlib, deterministic.

### 1D. Tool manifest `GET /api/tools.json`
Machine-readable description of every tool: name, description, method, path,
params schema, example request/response. Any tool-calling agent (Hermes,
OpenClaw, LangChain, whatever) can ingest this and self-configure. This file
IS the agent-agnostic claim.

### 1A. MCP adapter `mcp_adapter/desk_server.py` (Claude ecosystem)
Thin wrapper exposing the same operations as MCP tools:
`desk_status`, `list_signals`, `get_dispatch`, `get_validation_pack`,
`ask_desk`, `record_feedback`. Stdio first, streamable HTTP later (5B).
Dependency: `mcp` package isolated in `mcp_adapter/requirements.txt` —
pipeline never imports it.

### 1C. Machine discovery surface
- `llms.txt` + `agents.md` at root and served over HTTP — what the engine is,
  every endpoint, connect instructions per framework (Claude/MCP, Hermes,
  OpenClaw, plain curl).
- `signalctl ask "..."` subcommand (parity with API).
- README "For agents" section.

**Exit criteria (three frameworks, same engine):**
1. Claude: connect MCP server, ask the Guyana question, get cited answer.
2. Hermes: hit `/api/ask` + `/api/tools.json` via its HTTP tooling, same answer.
3. Any shell: `curl -X POST /api/ask` works with no agent at all.

## Phase 2 — Decision Desk UI (kill the boring)

### 2A. "Ask the desk" panel on the dashboard
Chat-style box above the fold wired to `/api/ask`. Suggestion chips:
"Explain the lead signal" / "What changed this cycle?" / "Draft an intro note
for Guyana". Deterministic answers render with artifact citations — reliable
in demos, no API key, no hallucination risk.

### 2B. Caribbean map as the hero visual
Inline SVG map, 13 watched countries. Per-country pulse sized by signal
confidence; color by kind (investment/climate/procurement). Click → drill
panel (uses `drill_country`). This becomes the product's visual identity.

### 2C. Live cycle theater
View driven by `/api/pipeline/stream` (SSE, already exists): sources light up,
signals form, dispatches route — visible motion. **Replay mode** ships with a
recorded cycle (`data/history/`) so the demo never depends on live network.

### 2D. Desk polish
- Validation pack: expandable per-signal (not lead-only), verdict filter.
- Cycle clock: "next cycle in …" countdown + last-cycle delta strip.
- Keep the editorial typography — the brand is fine; the *stillness* is the
  problem. Motion comes from 2B/2C, not a redesign.

**Exit criteria:** 30-second screen recording with zero typing shows motion,
a map, and a question being answered with citations.

## Phase 3 — Data depth (make the diligence claim honest)

Current weakness: World Bank annual data dressed as urgency; one procurement
notice. Frequency beats breadth.

### 3A. Tender watcher framework + 2 country adapters
`watchers/tenders/` with a shared base (fetch → normalise → dedupe →
`data/tenders/latest.json`). Start: Jamaica (GOJEP public notices) + Guyana
(PPC published awards/notices). CDB feed already covered. Cache raw snapshots
for scraper-fragility resilience.

### 3B. Validation pack v2
- Procurement matches from 3A (country-tagged, dated, closing-date aware —
  real 14-day windows at last).
- Sector confirmation: regional news RSS keyword match upgrades a sector
  hypothesis from `unconfirmed` → `corroborated` with the article as citation.
- Freshness: `last_validated_at` decay — packs older than N cycles downgrade
  advance → hold automatically.

### 3C. Operator discovery (assist, never fabricate)
Curated per-country registry files (`data/registries/<country>.json`) of
chambers, IPAs, sector associations — human-verified, append-only. Pack field
`credible_local_operators` stays empty unless registry-backed.

**Exit criteria:** Guyana pack shows ≥1 dated country procurement item and a
corroborated sector hypothesis with an external citation.

## Phase 4 — Proof-of-value loop (stretch)

- 4A. Two-way Telegram: inline buttons (Advanced / Forwarded / Not relevant)
  posting to `/api/feedback/apply` — closes the learning loop with real humans.
- 4B. Outcome ledger page: dispatch → response → boost applied → next-cycle
  effect. "What the desk got right" is the credibility page.
- 4C. Judge kit: 3-minute demo script, seeded replay cycle, one-page
  architecture diagram, `JUDGE_DEMO.md`.

---

## Phase 5 — Hosting (added per decision: demo env = both)

### 5A. Read-only public mode
`server.py --public` flag: GET endpoints + dashboard + `/api/ask` only.
All write endpoints (`/api/send/*`, `/api/feedback/apply`, `/api/delivery/*`,
`/api/domains/create`) return 403 unless a `DESK_ADMIN_TOKEN` header matches.
Pipeline loop stays on (it only reads public sources).

### 5B. Deploy
Small VPS (or fly.io/railway), domain, TLS via Caddy/nginx in front of the
Python server. systemd unit + 4-hourly pipeline already self-runs.
Remote MCP (streamable HTTP) exposed at `/mcp` on the same host — this is the
"any agent on the internet can query the Caribbean desk" moment.

### 5C. Demo failover drill
Rehearse: hosted dies → local replay mode within 30 seconds.

## Sequencing & cut-line (2–3 weeks, locked)

```
Week 1: 1B → 1D → 2A → 1C → 1A   (engine talks to ALL agents + humans)
Week 2: 2B → 2C → 2D → 5A → 5B   (engine looks alive + goes public)
Week 3: 3A → 4C → buffer          (honest procurement + judge kit)
Stretch: 3B → 3C → 5C
```

Execution model: Hermes builds from briefs in `planning/`; Claude writes the
briefs, reviews output against exit criteria, and handles strategy turns.
Week 1 brief: `planning/hermes-engine-week1-build-brief.md`.

Minimum winning demo = Phases 1 + 2 local. Hosted (5) is the backup wow;
3A de-risks diligence claims under scrutiny; 4C makes the demo repeatable.

## Risks

| Risk | Mitigation |
|---|---|
| MCP dep breaks "no-deps" purity | Isolated `mcp/` module; pipeline never imports it |
| Live demo network failure | Replay mode (2C) + cached snapshots (3A) |
| Tender portals block scraping | Snapshot cache; degrade to CDB-only honestly |
| Deterministic ask() feels limited | Suggestion chips steer to supported intents; LLM-backed mode optional later |
| Scope creep on UI redesign | 2D explicitly bounded; typography stays |

## Remaining open questions

1. Which 2 tender sources first — Jamaica (GOJEP) + Guyana (PPC) as proposed,
   or align to whichever country leads the signal each cycle?
   Default if unanswered: Jamaica + Guyana (lead signal is Guyana anyway).
2. ~~Hosting target~~ **DECIDED 2026-06-10: Vercel + GitHub Actions split**
   (fly.io ruled out — credits exhausted; must be $0).
   - GitHub Actions cron runs the pipeline every 4h and commits artifacts.
   - Vercel serves dashboard.html static + Python serverless functions for
     the read APIs (/api/ask, /api/tools.json, /api/validation-packs,
     /api/map-data, /api/status). Artifact commits auto-trigger redeploys.
   - Theater uses replay from committed data/history/ (client-side playback
     fallback if function streaming is unreliable). Live SSE stays local.
   - **5A shrinks**: no write endpoints are deployed at all, so the public
     instance is read-only by construction. Admin-token server hardening is
     deferred — only needed if a long-running host returns later.
   - Repo is currently PRIVATE: fine for Vercel Hobby + friends-via-URL;
     revisit visibility before buildathon submission (public = unlimited
     Actions minutes + judge inspection).
   - Brief: `planning/hermes-engine-5b-vercel-build-brief.md`.

## Risks added by hosting decision

| Risk | Mitigation |
|---|---|
| stdlib http.server exposed publicly | Read-only mode (5A) + reverse proxy in front; no writes without token |
| Hosted demo dies mid-judging | Failover drill (5C); local replay is always primary |
