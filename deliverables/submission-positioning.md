# Buildathon Deliverable Positioning — Caribbean Opportunity Dispatch

The product is **Caribbean Opportunity Dispatch**, not a dashboard.

The dashboard is only an operator console for proving the system is alive. The deliverables are the routed dispatches, persona dispatch packets, delivery manifest, regional thesis, why-now context, and feedback loop.

Caribbean Signal OS is the architecture underneath — the terms are distinct.

## Track Requirement Fit

Future Caribbean Track 08 asks for a continuous intelligence pipeline:

    Data -> Signal -> Packaging -> Distribution -> Action -> Capital

Caribbean Opportunity Dispatch (product) / Caribbean Signal OS (architecture) maps to this chain as follows:

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

## What We Should Demo (in order)

1. Run `bash run_pipeline.sh` — show the pipeline executing end-to-end
2. Open `outbox/opportunity_dispatches.md` — the product: routed dispatches with persona, channel, action, feedback status
3. Open `outbox/regional_thesis.md` — cross-cluster synthesis (investment + risk + pipeline + tourism + timing)
4. Open `outbox/why_now.md` — editorial calendar context for the current cycle
5. Open `outbox/feedback_review.md` — feedback loop: what was forwarded, replied to, opened, or changed a decision
6. Open `outbox/dispatch_packets/diaspora_investor.md` — persona-specific packet with action checklist and feedback options
7. Open `outbox/delivery_manifest.json` — channel-ready delivery manifest, one entry per dispatch
8. Open `outbox/channel_dispatch_log.md` — distribution routing by channel
9. Open `outbox/judge_brief.md` — full system brief with routing rationale
10. Run `python3 packagers/feedback_intake.py --list` — show CLI feedback intake working
11. Open `dashboard.html` — internal operator console (last, to confirm pipeline health)

## Product Framing

**Caribbean Opportunity Dispatch** is the first product surface:

- Routed dispatches for five personas: diaspora investor, ecosystem builder, regional operator, procurement watcher, policy/media
- Persona-specific packet files that show exactly what each recipient receives
- Delivery manifest that proves dispatches can move into channel adapters
- Each dispatch names a specific decision: investigate, validate, route, monitor, assess, or track
- Feedback loop learns which signals create action and adjusts future cycles
- Regional thesis synthesizes all signals into one actionable narrative
- Why-now context anchors every dispatch in seasonal and institutional timing

## Competition Gap

Existing tools stop at one layer:
- Data portals expose datasets but do not route decisions
- Newsletters explain market context but do not run a repeatable pipeline
- Procurement tools list tenders but do not connect them to market context
- Dashboards show status but do not package channel-ready action
- Investor catalogues list static opportunities but are not continuous data watchers

This fills the **last mile between public regional data and acted-on opportunity**.

## Dashboard Role

The dashboard is an **internal operator console** only:
- Pipeline health and source status
- Current regional thesis snapshot
- Top dispatches for judging inspection
- Dispatch Desk state: packet count, manifest count, channels
- Feedback loop state

It is not the user-facing deliverable. The product is the dispatch.
