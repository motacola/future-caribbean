# Demo Script — Caribbean Opportunity Dispatch

## One-liner

Caribbean Opportunity Dispatch turns fragmented Caribbean public data into decision-ready routes: what changed, who should act, what they should do next, and how feedback changes the next cycle.

**Track:** 10 — Open Track.

**Category:** Agentic market coordination infrastructure for fragmented Caribbean economies.

## 2-Minute Flow

1. **Problem**: Caribbean opportunity data exists across institutions, countries, and formats. That makes regional opportunities hard to see and slow to act on. The constraint is coordination, not data availability. Existing tools stop at portals, newsletters, or dashboards; they do not run a repeatable pipeline that ends in routed decisions.

2. **System**: Six watchers monitor World Bank, IDB, NOAA, NDBC, CARICOM, and CDB. A cross-source merger turns raw updates into composite signals. Editorial enrichment scores, narrates, and prepares them for routing.

3. **Product**: The Dispatch Desk groups repeated routes into decision clusters. Each cluster shows the signal, evidence, confidence, why-now context, persona routes, recommended action, delivery channel, and feedback status.

4. **Open Track fit**: This is not a Finance app, Disaster app, Food app, or Ocean app. Those are signal domains. The product is the cross-sector coordination layer that routes any relevant regional signal to the person most likely to act.

5. **Distribution**: Persona packets and a delivery manifest prove the last mile. Telegram/email are adapters; the product is the decision route.

6. **Feedback Loop**: Dispatches accumulate opens, forwards, replies, ignores, and decision-change markers. Boosts persist with decay, so the next cycle ranks similar signals differently.

7. **Ask the Dispatch Desk**: The dashboard includes an analyst rail for interrogating the cycle without reading every artifact. Click "Explain lead signal" or "Investor actions", or type a question like "draft Guyana investor note". Answers are deterministic, local, and cite artifact sources.

8. **Operator Audit**: The lower dashboard sections confirm the pipeline is alive: source health, dispatch counts, manifest state, packets, and feedback state.

## Headless query CLI

```bash
python3 agent/query.py explain-lead
python3 agent/query.py ask "what changed this cycle"
python3 agent/query.py ask "show investor actions"
python3 agent/query.py ask "draft Belize investor note"
```

## Command

```bash
bash run_pipeline.sh
```

## Files To Open During Demo (in order)

1. `dashboard.html` — start here: Dispatch Desk product view at top, operator audit below
2. `outbox/dispatch_desk.md` — judge/user-facing decision clusters in markdown
3. `outbox/dispatch_packets/diaspora_investor.md` — persona-specific delivery packet
4. `outbox/delivery_manifest.json` — channel handoff proof
5. `outbox/feedback_review.md` — feedback/learning loop
6. `outbox/regional_thesis.md` and `outbox/why_now.md` — synthesis and timing context
7. `outbox/opportunity_dispatches.json` — canonical route data if judges want to inspect internals

## Demo Close

The Open Track claim is not “we built a dashboard.” The claim is:

Fragmented public data → Agentic signal pipeline → Routed decisions → Feedback → Faster regional action

The Dispatch Desk makes that chain visible in one place. It shows how fragmented public regional data becomes a specific action for a specific person, with evidence and feedback attached.

Close with:

> We compress the time between public signal and economic action.
