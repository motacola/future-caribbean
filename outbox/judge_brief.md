# Caribbean Opportunity Dispatch — Judge Brief

Generated: 2026-05-28 03:46 UTC

## What This Proves

Caribbean Opportunity Dispatch is the product. Caribbean Signal OS is the architecture underneath. It watches public regional data, merges weak signals across sources, packages the strongest signals into opportunity dispatches with persona routing, and maintains a persistent feedback loop — the system learns which signals actually changed decisions.

## Live Run Snapshot

- Total raw signals generated: 26
- Sources represented: CARICOM, CDB, IDB, NDBC, NOAA, World Bank
- Countries/zones: 11
- New/updated this cycle: 1
- User-facing outputs: opportunity dispatches, regional thesis, why-now context, feedback review, judge brief

**Belize** — 2 signal(s), 4 source(s): 💼 Investment + 💎 Investment

🔴 — **💎 Investment — Belize**
   Belize: +701.0% multi-source capital surge — market entry window open
   Immediate | 100/100 | A - multi-source
   Immediate investigation. Belize has multi-source investment validation (3 signals converging). Priority: assess market entry options, identify existing operators.

## Supporting Decision Signals

**1.** 🔴 **💎 Investment — Barbados** — sustained
   Narrative: Barbados: +34.8% multi-source investment validated — opportunity active
   Score: 100/100 | Grade: A - multi-source
   Audience: investor/founder via Email brief + Telegram
   Decision: Immediate investigation. Barbados has multi-source investment validation (3 signals converging). Priority: assess market entry options, identify existing operators.

**2.** 🔴 **🏗️ Pipeline — CARICOM** — sustained
   Narrative: CARICOM: 6 active procurements — bidding window open
   Score: 96/100 | Grade: B - cross-source
   Audience: investor/founder via Email brief + Telegram
   Decision: Active procurement pipeline: CDB active procurement notices: 6. Priority: review CDB/IDB opportunities as lead list for project-based entry.

**3.** 🔴 **💼 Investment — Guyana** — sustained
   Narrative: Guyana: FDI trending at +860.3% — screening trigger active
   Score: 90/100 | Grade: B - cross-source
   Audience: investor/founder via Email brief + Telegram
   Decision: Immediate investigation. Guyana FDI signal (860.3% change) with active development datasets. Validate with local market intel.

**4.** 🟡 **🚢 Maritime — Caribbean** — new
   Narrative: Caribbean: signal detected
   Score: 82/100 | Grade: B - cross-source
   Audience: operator/resilience via Telegram/SMS alert
   Decision: Maritime hazard active: signal detected. Relevant for shipping, logistics, coastal operations.
   🆕 New this cycle

**5.** 🟡 **💼 Investment — St. Kitts and Nevis** — sustained
   Narrative: St. Kitts and Nevis: FDI trending at +41.1% — screening trigger active
   Score: 78/100 | Grade: B - cross-source
   Audience: investor/founder via Email brief + Telegram
   Decision: Validation priority. St. Kitts and Nevis FDI movement (41.1% change) signals opportunity. Cross-reference with sector data.

**6.** 🟢 **⚠️ Vulnerability — St. Vincent and the Grenadines** — sustained
   Narrative: St. Vincent and the Grenadines: economic stress indicators rising — portfolio review recommended
   Score: 69/100 | Grade: C - single-source
   Audience: policy/operator via Telegram digest
   Decision: Monitor. St. Vincent and the Grenadines showing economic stress (18.00%). Track next cycle. Escalates if additional stress indicators appear or existing ones worsen.

**7.** 🟢 **⚠️ Vulnerability — Suriname** — sustained
   Narrative: Suriname: economic stress indicators rising — portfolio review recommended
   Score: 56/100 | Grade: C - single-source
   Audience: policy/operator via Telegram digest
   Decision: Monitor. Suriname showing economic stress (16.23%). Track next cycle. Escalates if additional stress indicators appear or existing ones worsen.

## Routing Rationale

Each signal is routed to specific personas based on signal kind and evidence level. The routing logic is defined in `config/recipients.json`.

- **Active Storm** → Operator_Resilience
  - Operator Resilience: Named storm with track data is a time-critical operational event — response windows measured in hours
- **Cyclone Risk** → Operator_Resilience, Tourism_Logistics_Operator
  - Operator Resilience: Buoy pressure + marine alert convergence = elevated confidence for operational response trigger
  - Tourism Logistics Operator: Cyclone risk directly impacts tourism bookings and logistics routing — advance warning for contingency
- **Development Pipeline** → Regional_Operator, Procurement_Watcher, Founder_Operator
  - Regional Operator: Active procurement directly maps to operational capacity needs — first to respond wins
  - Procurement Watcher: CDB/IDB project pipeline is the primary lead source for project-based business development
  - Founder Operator: Procurement pipeline signals government and institutional spending direction — follow the money
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
- **Tourism Impact** → Tourism_Logistics_Operator, Founder_Operator
  - Tourism Logistics Operator: GDP growth in tourism-relevant economies signals demand trajectory — plan capacity accordingly
  - Founder Operator: Tourism-linked GDP growth in your operating country indicates broader consumer demand
- **Tropical Development** → Operator_Resilience
  - Operator Resilience: Pre-storm development monitoring allows staged preparedness without response fatigue

## Cycle Summary

Lead: Belize · 26 composite signal(s) · 1 new · 24 persistent
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
10. Open `dashboard.html` last as the operator console.

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
