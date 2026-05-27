# Demo Script — Caribbean Opportunity Dispatch

## One-liner

Caribbean Opportunity Dispatch turns fragmented Caribbean public data into routed opportunity and risk dispatches for the people who can act on them.

## 2-Minute Flow

1. **Problem**: Caribbean data exists across institutions, countries, and formats. That makes regional opportunities hard to see and slow to act on. Existing tools (portals, newsletters, dashboards) stop at data or context — none of them run a repeatable pipeline that ends in a routed decision.

2. **System**: Six watchers monitor World Bank, IDB, NOAA, NDBC, CARICOM, and CDB. A cross-source merger converts raw updates into composite intelligence signals. Editorial enrichment ranks, narrates, and routes them.

3. **Product**: Opportunity dispatches are the output — each dispatch targets a persona (diaspora investor, ecosystem builder, regional operator, procurement watcher, policy/media), specifies a channel (email, Telegram), names the decision it should trigger, and records whether it was acted on.

4. **Why Now**: Editorial calendar context (Q2 procurement cycle, tourism shoulder season) anchors each dispatch in real timing.

5. **Regional Thesis**: Cross-cluster synthesis connects investment momentum, risk flags, development pipeline, and timing into one actionable narrative each cycle.

6. **Feedback Loop**: Dispatches accumulate opens, forwards, replies, and decision-change signals. Boosts persist with decay — the system learns which signals create action.

7. **Operator Console**: The dashboard is an internal health view, not the product. It confirms the pipeline is alive — the product is in outbox/artifacts.

## Command

```bash
bash run_pipeline.sh
```

## Files To Open During Demo (in order)

1. `outbox/opportunity_dispatches.md` — the product: routed persona/action dispatches
2. `outbox/regional_thesis.md` — cross-cluster synthesis narrative
3. `outbox/why_now.md` — editorial calendar context
4. `outbox/feedback_review.md` — feedback/learning loop
5. `outbox/channel_dispatch_log.md` — distribution routing
6. `outbox/judge_brief.md` — system intelligence + routing rationale
7. `dashboard.html` — internal operator console (last, to confirm pipeline health)