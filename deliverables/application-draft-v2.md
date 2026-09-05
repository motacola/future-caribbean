# Future Caribbean Application Draft v2 — Abeng
# Caribbean Opportunity Dispatch
**Last updated: 2026-06-18**

---

## Track

**Open Track** — Agentic AI Systems / AI Infrastructure & Tooling / Multi-Agent Coordination

---

## Project name

**Caribbean Opportunity Dispatch** — powered by Abeng

---

## One-liner

Abeng watches fragmented Caribbean public data on a continuous 4-hour cycle, routes dated opportunity dispatches to the right person with pre-assembled diligence, and learns from feedback — exposing the same deterministic engine to humans and agents through HTTP, MCP, or CLI.

---

## Category (new category framing)

**Agent-ready opportunity coordination for fragmented emerging markets.**

This is not a dashboard, not a newsletter, and not a market intelligence report. It is the routing layer that sits between public data portals and the people (and agents) who should be acting on what those portals contain. The Caribbean is the live proof. The engine deploys to any fragmented regional economy.

---

## Problem

Caribbean public data already exists: World Bank FDI figures, IDB project datasets, CDB procurement feeds, CARICOM statistics, NOAA storm advisories, regional news. It's free, it's published regularly, and almost no one who could act on it ever sees it in time.

- A procurement window in Guyana closes in 6 days — no procurement watcher knows.
- FDI velocity in Belize has moved +701% — no diaspora investor has been routed to it.
- An oil & gas local content story in Guyana was published yesterday — no regional operator's diligence pack mentions it.

The gap is not data availability. The coordination layer is missing. Abeng fills it.

---

## Solution

Abeng is a **continuous multi-agent pipeline** that turns fragmented regional public data into routed, actionable dispatches — then learns from what gets acted on.

**Each 4-hour cycle:**

1. **Watcher agents** pull public data: World Bank, IDB, NOAA/NWS, NDBC buoys, CARICOM Statistics, CDB procurement, ECCB credit/deposit signals, AIS maritime data, regional news RSS, GOJEP and Guyana eProcure tender feeds
2. **Merger** combines weak signals across countries and sources into composite regional signals (cyclone risk, investment momentum, port congestion, supply chain pressure)
3. **Packagers** enrich each signal: confidence calibration, sector hypothesis corroboration via regional news, freshness decay, procurement matching, operator registry lookup
4. **Dispatch generator** routes 32+ dispatches per cycle to 7 personas with dated evidence, action window, and channel
5. **Validation packs** auto-assemble diligence: corroborated/unconfirmed hypotheses, live dated tenders, registry-backed operators, unresolved questions
6. **Feedback loop** applies opens/forwards/replies to reweight the next cycle

The output is not charts. The output is a **dispatch**: who should act, on what, by when, with what evidence, through what channel — and a record of whether they did.

---

## What's live today

This is a working system, not a proposal:

| Component | Status |
|---|---|
| Live tender data | 42 records: 22 from Guyana eProcure, 20 from Jamaica GOJEP — dated, closing-window-aware |
| Regional news corroboration | 109 articles from regional RSS + Google News; sector hypotheses upgraded corroborated/unconfirmed accordingly |
| Operator registries | 5 countries: Guyana, Belize, Jamaica, SVG, Barbados — curated, registry-backed, never fabricated |
| Validation packs | 6 packs with confidence calibration, freshness decay, action readiness scoring |
| Dispatch generation | 32 dispatches per cycle across 7 personas with routing rationale |
| Agent API | `POST /api/ask` — deterministic, cited, no LLM hallucination |
| MCP adapter | `mcp_adapter/desk_server.py` — any MCP-compatible agent queries the same engine |
| CLI | `abengctl.py ask "..."` — shell-compatible, OpenCall-ready |
| Domain instances | 2 live (Caribbean economic signals, climate/catastrophe risk) + 3 blueprints |
| Deployed | https://abeng.vercel.app |
| llms.txt + agents.md | Machine-readable contract for agent discovery |

---

## Honesty on simulated vs. real

- **Tender data**: real, live from public APIs and HTML pages
- **Regional news corroboration**: real, live RSS
- **Operator registries**: curated human-verified entries
- **Feedback loop**: the mechanism is real and working; responses in the current cycle are seeded/simulated — real recipient feedback replaces them in production
- **Confidence calibration**: real — macro-only signals without procurement or news corroboration are capped at ~68; multi-source with dated tenders score higher

---

## The agentic architecture (Open Track fit)

Abeng maps to all three Open Track build categories:

**Agentic AI systems**
- Watchers, merger, packagers, and feedback are distinct agents with defined inputs and outputs
- The reasoning agent (`reasoners/synthesis.py`) supports pluggable LLM via `LLM_BASE_URL` — ready for High-Rise H200 for synthesis while keeping `/api/ask` deterministic
- Human approval surfaces: validation pack `advance/hold/reject`, dispatch routing rationale, confidence floor before route

**AI infrastructure & tooling**
- Agent-agnostic by design: the same intelligence layer serves HTTP, MCP, CLI, and SSE stream
- `GET /api/tools.json` publishes the tool manifest
- Freshness decay, confidence calibration, and evidence fingerprinting are infrastructure, not one-off logic

**Multi-agent coordination**
- Watchers coordinate on a shared signal store; merger resolves conflicts across sources
- Domain registry (`domains/registry.py`) supports multiple independent instances with isolated signal spaces
- The Flue workflow harness defines cross-agent task graphs: `ask-dispatch`, `run-cycle`, `record-feedback`

---

## Why Open Track (not a sector track)

Finance, climate, food, ocean, and procurement are **signal domains inside the engine**, not the product category. Sector tracks reward solutions that change outcomes in one vertical. Open Track rewards the coordination layer that makes all verticals faster. That's Abeng.

---

## Users and the buyer story

**Primary user:** Regional founders/operators and diaspora investors who make capital-deployment or market-entry decisions.

**Decision the product changes:** "Should I investigate this market/procurement lane this week?" goes from unanswerable (signal buried in a portal) to answerable in one dispatch (dated tender + corroborated sector + registry operator + confidence grade).

**Realistic near-term buyers:**
- Diaspora investor networks (VC4A, Caribbean Angel Network) — consume validated opportunity dispatches via API or channel delivery
- Regional chambers of commerce — branded dispatch desks for member companies
- Accelerators (Cayman Enterprise City, local incubators) — validation pack API as portfolio screening tool
- Regional development institutions (CDB, Caribbean Export) — procurement signal routing for project pipeline awareness

**Revenue model candidates:** API subscription (per-query or monthly), white-label dispatch desk for institutions, validation pack API licensing.

We are not claiming current revenue. We are claiming a specific buyer with a specific unanswered question and a working system that answers it.

---

## Compute story (High-Rise H200)

`reasoners/synthesis.py` already has pluggable LLM config: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. The design is intentional: keep `/api/ask` deterministic and cited (no hallucination risk for agent callers), while using H200 inference for the cross-signal narrative synthesis and regional thesis that requires reasoning across many weak signals. One pipeline run is a few thousand tokens — well within the partner's offered budget.

---

## Why Caribbean / why now

The Caribbean is the ideal proof environment: 13+ small markets, high fragmentation, regional institutions with public data, diaspora capital looking for signals, climate exposure that creates both risk and procurement opportunity, and procurement-driven development that creates recurring dated windows.

What works here works in any fragmented regional economy: West Africa, Southeast Asia, island states with diaspora capital networks. The Caribbean is not a ceiling; it's the testbed.

---

## The defensible moat

1. **Corroboration engine** — sector hypotheses are automatically upgraded from `unconfirmed` to `corroborated` when regional news matches; confidence is calibrated down when they don't. Competitors can't fake this with a static catalogue.
2. **Dated procurement matching** — live tender closing dates inside validation packs create urgency that weekly newsletters structurally cannot produce.
3. **Feedback-adjusted routing** — signals that generate forwards/replies rank higher next cycle; ignored signals decay. This compounds over time.
4. **Agent-agnostic contract** — HTTP + MCP + CLI means any coordination framework (OpenCall, Flue, custom) can query the same deterministic engine. Lock-in is to the data and reasoning, not to a particular AI runtime.

---

## Five-year potential

Year 1: Caribbean economic + climate signal instances live; regional chambers and diaspora networks as first institutional subscribers.  
Year 2: Second geography (West Africa or Pacific small states) via domain configurator; API revenue from 3–5 institutional clients.  
Year 3: Sector-specific signal desks (capital markets, supply chain, compliance) as licensable domain blueprints.  
Year 5: Abeng becomes the coordination API layer for fragmented-market intelligence globally — the "who should act on this" layer that sector analysts, AI agents, and coordination platforms connect to.

---

## Build artifacts (verifiable today)

- Deployed: https://abeng.vercel.app
- Source: github.com/motacola/future-caribbean (private; share access on request)
- API: `curl -s -X POST https://abeng.vercel.app/api/ask -H "Content-Type: application/json" -d '{"question":"what changed this cycle"}'`
- MCP: `mcp_adapter/desk_server.py` — runs locally, queries same artifacts
- CLI: `python3 cli/abengctl.py ask "show Guyana dispatches"`
- Validation pack: `outbox/validation_packs/enhanced-invest-guyana.md` — live, dated procurement, corroborated sector, registry operators

---

## Demo path (dispatch-first, not dashboard-first)

1. **Problem** (30s): "Public signals die in portals. A tender closes in 6 days — no one knows."
2. **Pipeline** (30s): `bash run_pipeline.sh` — watch watchers → merger → packs execute
3. **Dispatch queue** (45s): `outbox/opportunity_dispatches.md` — 32 dispatches, persona-routed, dated
4. **One dispatch end-to-end** (45s): Guyana oil & gas — corroborated sector, 6 live tenders, 3 registry operators, calibrated confidence, action window
5. **Agent query** (30s): `curl -s POST /api/ask '{"question":"what changed this cycle"}'` — deterministic, cited, same engine
6. **Feedback** (30s): `outbox/feedback_review.md` — what was acted on, what changed next cycle
7. **Scale story** (30s): Configurator wizard — spin up a second domain in 2 minutes

Total: ~3.5 minutes. Dashboard is available for deep-dive questions, not the opening.

---

## Closing claim

Abeng compresses the time between a public signal and the person who should act on it. The Caribbean is where it runs today. Any fragmented regional economy is where it runs tomorrow.

---

## Notes for the application form

**Q: What is your prior build artifact?**
Deployed API at https://abeng.vercel.app + source repository. The `/api/ask` endpoint, validation packs in `/outbox/validation_packs/`, and live tender data are all runnable and inspectable.

**Q: What frameworks / tools are you using?**
Pure Python pipeline (no framework lock-in); stdlib HTTP server; MCP adapter; Flue workflow harness; pluggable LLM via `LLM_BASE_URL` (currently Ollama/Gemma 4 locally, ready for High-Rise H200).

**Q: How does this use agentic AI?**
Multi-agent pipeline with distinct watcher, merger, packaging, and reasoning agents. The agent API (`/api/ask`, `/api/tools.json`, MCP adapter, `abengctl`) makes the same deterministic intelligence layer accessible to any AI agent or coordination framework. Feedback loop adjusts agent routing across cycles.

**Q: Why Open Track?**
This is coordination infrastructure, not a vertical app. Open Track is the only track that rewards the engine that makes every other track faster.

**Q: What would you do with the 21-day sprint?**
Week 1: Real Telegram feedback path (inline buttons → `/api/feedback/apply`), outcome ledger, confidence calibration v2.  
Week 2: High-Rise H200 integration for synthesis reasoning, second geography proof (West Africa blueprint → partial live), institutional buyer outreach with validation pack API demo.
