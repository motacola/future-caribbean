# Caribbean Opportunity Dispatch — Judge Demo Walkthrough

A guided tour of the system, artifact by artifact. Each step proves a specific claim about what the product does and why it matters.

**Submission track:** 10 — Open Track.

**Category:** Agentic market coordination infrastructure for fragmented Caribbean economies.

**Core claim:** Caribbean Opportunity Dispatch compresses the time between public signal and economic action.

---

## Step 1: The Problem (Context)

Public regional data for the Caribbean is fragmented across 10+ institutions — World Bank, IDB, CDB, CARICOM, NOAA, NDBC, and national statistics offices. Each publishes independently. No single view exists.

The intended consumer — diaspora investors, regional operators, ecosystem builders — has to pull from all of them manually. Most don't. The data sits in PDFs and spreadsheets, never reaching the people who could act on it.

**Signal OS exists because the gap isn't data availability. It's data routing.**

That is why this belongs in Open Track: the product is a reusable coordination layer, not a single-sector app.

---

## Step 2: The Pipeline (Architecture)

Run once:

```bash
bash run_pipeline.sh
```

This executes:

| Step | What it does | Proves |
|------|-------------|--------|
| 6 watchers | Poll World Bank, IDB, CDB, CARICOM, NOAA, NDBC | Live public data ingestion |
| Cross-source merger | Combines 25+ weak signals across sources into composite signals | Signal detection, not scraping |
| Feedback apply | Reads previous-cycle feedback → computes per-signal boosts | Persistent learning loop |
| Channel outputs | Enriches + scores signals → produces briefs (Telegram, investor, diaspora, judge) | Editorial judgment |
| Opportunity dispatch | Routes signals as action dispatches by persona | Decision routing |
| Dispatch packets | Splits dispatches into persona-specific `.md` packets | Action proof — per-persona delivery |
| Delivery manifest | Generates a machine-readable delivery manifest | Distribution proof — one entry per dispatch |
| Why-now context | Checks editorial calendar for seasonal/timing relevance | Temporal awareness |
| Regional thesis | Connects investment, risk, pipeline, tourism into one narrative | Cross-cluster intelligence |
| Feedback record | Saves cycle's dispatch history for next-cycle adaptation | The feedback loop |

**Total artifacts generated per cycle:** 8+ user-facing outputs, 1 feedback state file, 1 operator console.

---

3. Open `dashboard.html` — Today's Desk first

**What this proves:** The product is a dispatch desk, not a data viewer. The top section shows the coordination chain in one place.

The "Today's Desk" section shows multiple live signals per cycle — each with country, signal type, pct change, A/B/C evidence grade, confidence status, and persona routes. Guyana leads at +860.3% (A-grade, multi-source). Belize follows at +701.0%. SVG shows a conflicted signal: FDI up 88.2% but unemployment at 18%. CARICOM procurement shows 6 active bidding windows.

The persona section shows seven audience cards — each with a complete action sentence. Same signal, different action per persona. This is routing intelligence, not a broadcast.

---

## Step 4: Interact with the analyst rail

Use the "Ask about today's briefing" panel to test deterministic querying. Click "Explain the lead" for a substantive 3-4 sentence answer citing Guyana FDI evidence and multi-source validation. Click "Belize" or "SVG conflict" for country-specific breakdown. Click "Draft a note" for a ready-to-send investor email. Type any country, signal type, or "feedback loop" in the input field — all answers are deterministic, local, read-only from embedded data.

**What this proves:** The cycle is interrogable without reading every artifact.

---

## Step 5: Review the feedback table

Scroll to "Delivery responses" — the table shows dispatch-level feedback with three columns: dispatch name, last feedback action, and numerical effect on next cycle. Positive values (teal) mean the signal was forwarded, replied to, or changed a decision. Negative values (coral) mean it was ignored. Boosts decay 50% per cycle.

**What this proves:** The feedback loop is consequential, not decorative. Recipient behavior directly changes next-cycle priority.

---

## Step 6: Open the persona packets

Open `outbox/dispatch_packets/diaspora_investor.md` and `outbox/dispatch_packets/founder_operator.md` to compare how different personas receive the same signal formatted differently.

Open `outbox/delivery_manifest.json` — the machine-readable map of 29 dispatches to channels.

Open `outbox/regional_thesis.md`, `outbox/why_now.md`, and `outbox/feedback_review.md` for synthesis, timing context, and the feedback/learning loop documentation.

**What this proves:** Distribution readiness — the last mile before external channel integration is proven.

---

## Step 7: Open the outbox artifacts

Open `outbox/opportunity_dispatches.json` only if judges want to inspect the canonical route data.

Run `python3 agent/query.py ask "show investor actions"` to demonstrate the headless query CLI.

**What this proves:** The system is headless-queryable — web UI, CLI, and future API all share the same deterministic query engine.

---

## Step 8: Review the lower dashboard operator/audit sections

**What this proves:** The same page also includes operator/audit health below the product sections. It shows:
- Source health (6 sources tracked)
- All 13 themes/clusters with confidence, evidence, and persona routes
- Feedback counts (50 total responses across the cycle)
- System counts (themes, dispatches, responses, sources, countries)

The top of the dashboard is the dispatch desk product view; the lower sections are what an operator uses to confirm the pipeline is alive.

---

## Summary: The Open Track Claim

Caribbean Opportunity Dispatch is not a dashboard. It is an **agentic market coordination system** that:

1. **Detects** signals from fragmented public data (6 watchers, 10+ sources)
2. **Judges** them with editorial enrichment (score bands, evidence grades, narrative titles)
3. **Routes** them to specific personas with recommended actions (31 dispatches, 8 personas)
4. **Distributes** them through appropriate channels (Email, Telegram, digest)
5. **Learns** from feedback (persistent state, decayed boosts, next-cycle adjustment)
6. **Synthesizes** a cross-cluster thesis connecting capital, risk, pipeline, and timing
7. **Contextualizes** every dispatch with seasonal and event awareness

The product output is the Dispatch Desk — grouped, routed, actionable decision clusters that tell specific personas *what changed, why it matters now, and what to do next.*

Finance, disaster, food, ocean, tourism, and procurement are all valid signal domains inside the system. Open Track is the correct submission category because the product is the routing and coordination infrastructure across those domains.

---

*Generated: 2026-05-26*
