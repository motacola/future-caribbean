# Caribbean Opportunity Dispatch — Judge Brief

Generated: 2026-08-18 16:45 UTC

## What This Proves

Caribbean Opportunity Dispatch is the product. Caribbean Signal OS is the architecture underneath. It watches public regional data, merges weak signals across sources, packages the strongest signals into opportunity dispatches with persona routing, and maintains a persistent feedback loop — the system learns which signals actually changed decisions.

## Live Run Snapshot

- Total raw signals generated: 64
- Sources represented: CARICOM, CCRIF SPC, CDB, ECCB, IDB, NDBC, World Bank
- Countries/zones: 39
- New/updated this cycle: 7
- User-facing outputs: opportunity dispatches, regional thesis, why-now context, feedback review, judge brief

**Guyana** — 3 signal(s), 4 source(s): 💼 Investment + 🏖️ Tourism + 💎 Investment

🔴 — **💎 Investment — Guyana**
   Guyana: +860.3% capital surge on a single official source — market entry window open
   Immediate | 100/100 | C - single-source
   Immediate investigation. Guyana has multi-source investment validation (3 signals converging). Priority: assess market entry options, identify existing operators.

## Supporting Decision Signals

**1.** 🔴 **supply_chain_signal — Belize** — sustained
   Narrative: Belize: signal detected
   Score: 100/100 | Grade: A - multi-source
   Audience: regional intelligence via Telegram digest
   Decision: Immediate — Belize: supply_chain_signal (signal detected). Validate locally.

**2.** 🔴 **💎 Investment — Suriname** — sustained
   Narrative: Suriname: +206.0% investment movement, one source — needs corroboration
   Score: 98/100 | Grade: C - single-source
   Audience: investor/founder via Email brief + Telegram
   Decision: Immediate investigation. Suriname has multi-source investment validation (3 signals converging). Priority: assess market entry options, identify existing operators.

**3.** 🔴 **🏗️ Pipeline — CARICOM** — sustained
   Narrative: CARICOM: 7 active procurements — bidding window open
   Score: 95/100 | Grade: B - cross-source
   Audience: investor/founder via Email brief + Telegram
   Decision: Active procurement pipeline: CDB active procurement notices: 7. Priority: review CDB/IDB opportunities as lead list for project-based entry.

**4.** 🟡 **ccrif_payout — St. Kitts and Nevis** — intensified
   Narrative: St. Kitts and Nevis: signal detected
   Score: 84/100 | Grade: C - single-source
   Audience: regional intelligence via Telegram digest
   Decision: Validation — St. Kitts and Nevis: ccrif_payout (signal detected). Validate locally.
   ⬆️ Strengthened (+8 pts)

**5.** 🟡 **ccrif_payout — Dominica** — intensified
   Narrative: Dominica: signal detected
   Score: 84/100 | Grade: C - single-source
   Audience: regional intelligence via Telegram digest
   Decision: Validation — Dominica: ccrif_payout (signal detected). Validate locally.
   ⬆️ Strengthened (+8 pts)

**6.** 🟡 **eccb_credit_surge — Eastern Caribbean Currency Union** — sustained
   Narrative: Eastern Caribbean Currency Union: 5.8%
   Score: 76/100 | Grade: C - single-source
   Audience: regional intelligence via Telegram digest
   Decision: Validation — Eastern Caribbean Currency Union: eccb_credit_surge (5.8%). Validate locally.

**7.** 🟡 **💼 Investment — Barbados** — sustained
   Narrative: Barbados: FDI trending at +34.8% — screening trigger active
   Score: 75/100 | Grade: B - cross-source
   Audience: investor/founder via Email brief + Telegram
   Decision: Validation priority. Barbados FDI movement (34.8% change) signals opportunity. Cross-reference with sector data.

## Routing Rationale

Each signal is routed to specific personas based on signal kind and evidence level. The routing logic is defined in `config/recipients.json`.

- **Active Storm** → Operator_Resilience
  - Operator Resilience: Named storm with track data is a time-critical operational event — response windows measured in hours
- **Ccrif Payout** → Diaspora_Investor, Policy_Media, Operator_Resilience, Ecosystem_Builder
  - Diaspora Investor: CCRIF payout = verified hazard + immediate liquidity = reconstruction investment window opens
  - Policy Media: Parametric payout = quantified sovereign risk event = fiscal impact story
  - Operator Resilience: Payout confirms hazard severity = operational recovery capital available
  - Ecosystem Builder: Payout triggers regional reconstruction = supply chain, logistics, construction pipeline
- **Cyclone Risk** → Operator_Resilience, Tourism_Logistics_Operator
  - Operator Resilience: Buoy pressure + marine alert convergence = elevated confidence for operational response trigger
  - Tourism Logistics Operator: Cyclone risk directly impacts tourism bookings and logistics routing — advance warning for contingency
- **Development Pipeline** → Regional_Operator, Procurement_Watcher, Founder_Operator
  - Regional Operator: Active procurement directly maps to operational capacity needs — first to respond wins
  - Procurement Watcher: CDB/IDB project pipeline is the primary lead source for project-based business development
  - Founder Operator: Procurement pipeline signals government and institutional spending direction — follow the money
- **Eccb Credit Surge** → Diaspora_Investor, Founder_Operator, Ecosystem_Builder, Regional_Operator
  - Diaspora Investor: Credit surge = banking system confidence = deploy capital alongside local lending
  - Founder Operator: Credit growth = working capital available = demand for local goods/services rising
  - Ecosystem Builder: Credit expansion = fintech, SME lending, financial inclusion opportunities
  - Regional Operator: Deposit growth = local liquidity = procurement and supply chain capacity
- **Eccb Deposit Growth** → Diaspora_Investor, Ecosystem_Builder, Regional_Operator
  - Diaspora Investor: Deposit growth = institutional confidence = favorable capital environment
  - Ecosystem Builder: Deposit surge = remittance inflow or FDI settlement = ecosystem liquidity
  - Regional Operator: Deposit base = procurement capacity payment assurance
- **Economic Vulnerability** → Diaspora_Investor, Policy_Media
  - Diaspora Investor: Vulnerability signals change risk profiles — reassess exposure and timing
  - Policy Media: Economic stress indicators drive policy response and media narratives
- **Enhanced Investment** → Diaspora_Investor, Ecosystem_Builder, Founder_Operator
  - Diaspora Investor: Multi-source validation reduces screening risk — capital follows verified signals
  - Ecosystem Builder: Cross-country investment velocity signals where to focus ecosystem support and founder matching
  - Founder Operator: Multi-source investment lift indicates growing market that may support new entry or expansion
- **Food Security** → Ecosystem_Builder, Policy_Media
  - Ecosystem Builder: Food trade data reveals supply chain gaps that local founders and agri-tech can fill
  - Policy Media: Food security is a regional stability indicator — tracks pressure points before they become crises
- **Investment Signal** → Diaspora_Investor, Founder_Operator
  - Diaspora Investor: Single-source FDI movement is a screening trigger, not a deployment signal — start diligence
  - Founder Operator: FDI movement in your operating country signals competition or demand growth — assess positioning
- **Maritime Hazard** → Operator_Resilience, Tourism_Logistics_Operator
  - Operator Resilience: High-wind + marine alert confirmation requires safety response and shipping route adjustments
  - Tourism Logistics Operator: Maritime hazards affect island supply chains and tourism transport schedules
- **Port Activity Surge** → Regional_Operator, Procurement_Watcher, Founder_Operator, Ecosystem_Builder
  - Regional Operator: Vessel surge at key port = immediate cargo handling and transport demand
  - Procurement Watcher: High port activity = import/export volume up = procurement pipeline likely expanding
  - Founder Operator: Port throughput growth = build logistics, cold storage, last-mile services here
  - Ecosystem Builder: Port activity = trade corridor health = regional integration indicator
- **Port Congestion** → Regional_Operator, Operator_Resilience, Procurement_Watcher
  - Regional Operator: Congestion = vessels waiting = delays, demurrage costs, rerouting needed immediately
  - Operator Resilience: Slow vessels in port zone = operational bottleneck = activate contingency routes
  - Procurement Watcher: Congestion at transshipment hub = procurement delivery risk = adjust schedules
- **Shipping Corridor** → Regional_Operator, Ecosystem_Builder, Founder_Operator
  - Regional Operator: Consistent eastbound/westbound traffic = reliable corridor for scheduled services
  - Ecosystem Builder: Active corridor = trade route validation = port infrastructure and services investment case
  - Founder Operator: Known shipping lane = predictable transit times = build distribution hub here
- **Supply Chain Signal** → Regional_Operator, Procurement_Watcher, Founder_Operator
  - Regional Operator: Active procurement + stable maritime = real supply chain corridor opportunity — first to respond wins
  - Procurement Watcher: CDB procurement aligned with maritime stability = viable logistics corridors for project-based entry
  - Founder Operator: Supply chain gaps + procurement pipeline = where to build logistics, warehousing, or last-mile services
- **Tourism Impact** → Tourism_Logistics_Operator, Founder_Operator
  - Tourism Logistics Operator: GDP growth in tourism-relevant economies signals demand trajectory — plan capacity accordingly
  - Founder Operator: Tourism-linked GDP growth in your operating country indicates broader consumer demand
- **Tropical Development** → Operator_Resilience
  - Operator Resilience: Pre-storm development monitoring allows staged preparedness without response fatigue

## Cycle Summary

Lead: Guyana · 64 composite signal(s) · 7 updated · 10 intensified · 36 persistent
## Judge Demo Path

1. Run `bash run_pipeline.sh`.
2. Open `outbox/opportunity_dispatches.md` to show routed persona/action dispatches.
3. Open `outbox/regional_thesis.md` for the cross-cluster synthesis narrative.
4. Open `outbox/why_now.md` for the editorial calendar context.
5. Browse `outbox/dispatch_packets/` for persona-specific dispatch packets.
6. Open `outbox/delivery_manifest.json` for the machine-readable delivery manifest.
7. Open `outbox/channel_dispatch_log.md` to show distribution routing.
8. Open `outbox/feedback_review.md` to show the feedback/learning loop.
9. Open `outbox/judge_brief.md` for the system and routing rationale.
10. Open the dashboard site (`python3 server.py`, then `/`) last as the operator console.

## The Feedback Loop (Live)

Feedback is persistent across cycles. The previous run logged 4 feedback events:

- **Guyana enhanced_investment** was forwarded → this cycle gets +6 boost
- **CARICOM development_pipeline** was replied to → this cycle gets +2 boost
- **St. Vincent economic_vulnerability** changed a decision → this cycle gets +10 boost
- **Trinidad enhanced_investment** was ignored → slightly negative or neutral this cycle

These boosts are written to `data/feedback/current_boosts.json` and read by
`editorial_enrichment.py` at the start of each cycle. The score adjustment
persists through decay: each cycle halves the effective boost.

## Regional Thesis Pattern

The system produces one cross-cluster synthesis per cycle that connects
investment momentum, risk flags, development pipeline, tourism signals, and
timing context into a single actionable narrative. This is what makes the
product feel like intelligence, not a ranked list.

## Why Now? Editorial Calendar

`config/editorial_calendar.json` defines seasonal windows and upcoming events.
Each dispatch and thesis includes context about why this signal matters
at this point in the year — hurricane season, procurement cycles, tourism
windows, and regional events.
