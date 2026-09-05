# Buildathon Deliverable Positioning — Abeng

The product is **Abeng**, not a dashboard.

The dashboard is only an operator console for proving the system is alive. The deliverables are the routed dispatches, persona dispatch packets, delivery manifest, regional thesis, why-now context, and feedback loop.

## Track Fit

**Chosen track: 10 — Open Track.**

Abeng belongs in Open Track because it is not a sector-specific app. It is an agentic market coordination layer for fragmented Caribbean economies.

Finance, disaster risk, food, ocean, tourism, energy, and procurement are signal domains inside the system. The product category is the cross-sector routing infrastructure that turns those signals into decision-ready dispatches for specific people.

The Open Track claim:

    Fragmented public data -> agentic signal pipeline -> routed decisions -> feedback -> faster regional action

Abeng maps to this chain as follows:

| Requirement | Implementation |
|---|---|
| Combine at least two independent datasets | Six public sources: World Bank, IDB, NOAA, NDBC, CARICOM, CDB |
| Multiple Caribbean countries | 13 countries plus regional marine/weather zones |
| Live repeatable signal | Cron-runnable watchers + cross-source merger |
| Distributable outputs | Opportunity dispatches, regional thesis, why-now, feedback review, dispatch packets, delivery manifest |
| Defined user and decision | Seven personas — diaspora investor, founder/operator, ecosystem builder, regional operator, procurement watcher, policy/media, tourism/logistics — each dispatch names the decision |
| Feedback/learning loop | Persistent feedback state with boost decay — forwarded, replied-to, and decision-change events uprank similar signals next cycle |
| Distribution readiness | Dispatch packets per persona, channel-ready delivery manifest, feedback intake CLI |
| Continuous operation | run_pipeline.sh runs watchers, merger, packagers, feedback loop, dispatch packets, manifest, operator console |

## Why Not A Sector Track

| Track | Why it partially fits | Why Open Track is stronger |
|---|---|---|
| Finance, Payments & MSME Capital | The system routes investment, FDI, procurement, and diaspora capital signals | Finance is one output lane, not the whole product |
| Climate Risk & Disaster Coordination | NOAA/NDBC risk signals can route to operators and policy/media users | Disaster coordination is one signal family, not the core architecture |
| Ocean Systems & Blue Economy | Marine and weather data can support maritime, tourism, and logistics decisions | Ocean is one data domain inside a broader regional intelligence layer |
| Food Systems & Supply Chains | CARICOM food/security signals can identify supply chain pressure | Food is a vertical use case, not the product category |
| Tourism & Transportation | Tourism windows and airlift/demand signals can be routed | Tourism is another downstream decision lane |

Open Track lets the submission tell the truth: this is coordination infrastructure across fragmented real-economy signals.

## What We Should Demo (in order)

1. Run `bash run_pipeline.sh` — show the pipeline executing end-to-end
2. Open the desk at `/` (`python3 server.py`, then `http://localhost:8080/`) — start with the Dispatch Desk product view, then scroll to operator/audit health
3. Open `outbox/dispatch_desk.md` — the primary Open Track surface: decision clusters, persona routes, evidence, action, feedback
4. Open `outbox/dispatch_packets/diaspora_investor.md` — persona-specific packet with action checklist and feedback options
5. Open `outbox/delivery_manifest.json` — channel-ready delivery manifest, one entry per dispatch
6. Open `outbox/feedback_review.md` — feedback loop: what was forwarded, replied to, opened, or changed a decision
7. Open `outbox/regional_thesis.md` and `outbox/why_now.md` — cross-cluster synthesis and timing context
8. Run `python3 packagers/feedback_intake.py --list` — show CLI feedback intake working
9. Open `outbox/opportunity_dispatches.json` only if judges want the canonical route data

## Product Framing

**Abeng** is the first product surface:

- Routed decision clusters for seven personas: diaspora investor, founder/operator, ecosystem builder, regional operator, procurement watcher, policy/media, tourism/logistics
- Dispatch Desk view that groups repeated persona routes under one signal so the decision, evidence, action, and feedback are visible at once
- Persona-specific packet files that show exactly what each recipient receives
- Delivery manifest that proves dispatches can move into channel adapters
- Each dispatch names a specific decision: investigate, validate, route, monitor, assess, or track
- Feedback loop learns which signals create action and adjusts future cycles
- Regional thesis synthesizes all signals into one actionable narrative
- Why-now context anchors every dispatch in seasonal and institutional timing
- Ask the Dispatch Desk analyst rail for drilldowns, evidence explanations, persona filters, and copyable draft briefs
- Headless query CLI (`agent/query.py`) so web, CLI, Telegram, and future API clients can share the same deterministic intelligence layer

## Competition Gap

Existing tools stop at one layer:
- Data portals expose datasets but do not route decisions
- Newsletters explain market context but do not run a repeatable pipeline
- Procurement tools list tenders but do not connect them to market context
- Dashboards show status but do not package channel-ready action
- Investor catalogues list static opportunities but are not continuous data watchers

This fills the **last mile between public regional data and acted-on opportunity**.

The short version:

> Abeng compresses the time between public signal and economic action.

## Dashboard Role

The dashboard is an **internal operator console** only:
- Pipeline health and source status
- Current regional thesis snapshot
- Top dispatches for judging inspection
- Dispatch Desk state: packet count, manifest count, channels
- Feedback loop state

It is not the user-facing deliverable. The product is the dispatch.
