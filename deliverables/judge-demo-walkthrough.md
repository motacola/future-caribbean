# Caribbean Opportunity Dispatch — Judge Demo Walkthrough

A guided tour of the system, artifact by artifact. Each step proves a specific claim about what the product does and why it matters.

---

## Step 1: The Problem (Context)

Public regional data for the Caribbean is fragmented across 10+ institutions — World Bank, IDB, CDB, CARICOM, NOAA, NDBC, and national statistics offices. Each publishes independently. No single view exists.

The intended consumer — diaspora investors, regional operators, ecosystem builders — has to pull from all of them manually. Most don't. The data sits in PDFs and spreadsheets, never reaching the people who could act on it.

**Signal OS exists because the gap isn't data availability. It's data routing.**

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

## Step 3: Open `outbox/opportunity_dispatches.md`

**What this proves:** The system doesn't just detect signals — it routes them as concrete actions to specific personas.

Each dispatch has:
- **Editorial title** (answers "why does this matter")
- **Target persona** (investor, founder, operator, ecosystem builder)
- **Channel** (Telegram, email, digest)
- **Why this persona** (routing rationale)
- **Recommended action** (what to do next)
- **Evidence grade** (A = multi-source, B = cross-source, C = single-source)

Current cycle (2026-05-26): **31 dispatches** routed to 6 persona types.

**Example route:**

```
Guyana: +860.3% multi-source capital surge — market entry window open
  To: Diaspora Investor • Via: Email brief + Telegram
  Why: Multi-source validation reduces screening risk
  Action: Investigate Guyana as a capital deployment target this cycle.
  
  To: Ecosystem Builder • Via: Telegram
  Why: Cross-country investment velocity signals where to focus support
  Action: Route Guyana opportunity to relevant founders and investors.
```

Same signal → different actions per persona. This is routing intelligence, not a broadcast.

---

## Step 4: Open `outbox/regional_thesis.md`

**What this proves:** The system connects individual signals into a single regional narrative. This is what distinguishes intelligence from a list.

Current thesis:

> Capital momentum is strongest in **Guyana (+860.3%)**, followed by Belize, St. Vincent and the Grenadines. However, **SVG and Suriname** also carry elevated vulnerability indicators — investment signals from these countries require deeper diligence before committing capital. Development pipeline remains active (6 CDB procurements) — the **bidding window is open** for project-based entry. Tourism-related growth signals visible in Antigua, Guyana, St. Kitts — demand-side indicators for capacity planning.

The thesis synthesizes 5 signal types across 10 countries into 3 sentences plus actionable recommendations. No single watcher could produce this. Only a cross-source, cross-kind system can.

---

## Step 5: Open `outbox/why_now.md`

**What this proves:** The system has temporal awareness — it knows what matters *this week*, not just *what changed*.

Current context:

```
🟢 Tourism Shoulder Season — Post-peak period. Early indicators of summer
   demand trajectory are most valuable now.
   → Track early summer booking and airlift data
🔴 Q2 Procurement Cycle — CDB and IDB typically issue mid-year procurement
   rounds in Q2. Pipeline data especially actionable now.
   → Review procurement pipeline for active bidding opportunities
```

Each dispatch kind is cross-referenced against the calendar. Investment pipeline dispatches carry Q2 procurement context. Tourism dispatches carry shoulder season context. The editorial calendar (`config/editorial_calendar.json`) defines 5 seasonal windows and 5 upcoming events, including hurricane season (Jun-Nov), the Future Caribbean Buildathon (July 15), and COP climate negotiations.

---

## Step 6: Open `outbox/channel_dispatch_log.md`

**What this proves:** Dispatches are routed per persona to specific channels — Email brief, Telegram, Telegram digest. Not a single feed.

Current routing:

| Channel | Dispatches | Best for |
|---------|-----------|----------|
| Email brief + Telegram | 10 | Investors, procurement watchers — need signal + detailed context |
| Telegram | 17 | Founders, operators — time-sensitive, actionable alerts |
| Telegram digest | 3 | Broad awareness — vulnerability, food security |
| Email brief | 1 | Procurement pipeline detail |

This is the distribution layer. The same system can route to Slack, WhatsApp, SMS, or any channel with a bridge.

---

## Step 7: Open `outbox/feedback_review.md`

**What this proves:** The feedback loop is real, not simulated.

4 feedback events from the previous cycle:

| Dispatch | Feedback | Effect this cycle |
|----------|----------|-------------------|
| Guyana enhanced_investment | 📤 forwarded | +6 boost to Guyana enhanced signals |
| CARICOM development_pipeline | 💬 replied | +2 boost to pipeline signals |
| SVG economic_vulnerability | 🔀 decision_changed | +10 boost — highest weight |
| Trinidad enhanced_investment | 👁️ opened only | +1 (minimal signal) |

The feedback state is read at pipeline start and written at pipeline end. Boosts decay by half each cycle. Next cycle, these same signals will have different scores based on accumulated feedback history.

**This is the closed-loop intelligence model:** dispatch → receive feedback → adapt scoring → dispatch differently.

---

## Step 8: Open `outbox/dispatch_packets/` and `outbox/delivery_manifest.json`

**What this proves:** The system produces distribution-ready outputs, not just internal artifacts.

Each persona gets a dedicated packet under `outbox/dispatch_packets/`:

| Packet | Dispatches | Channel |
|--------|-----------|---------|
| `diaspora_investor.md` | 10 | Email brief + Telegram |
| `founder_operator.md` | 9 | Telegram |
| `ecosystem_builder.md` | 5 | Telegram |
| `policy_media.md` | 3 | Telegram digest |
| `procurement_watcher.md` | 1 | Email brief |
| `regional_operator.md` | 1 | Telegram |

Each packet contains the dispatches routed to that persona with:
- Editorial title and score
- Recommended action
- Evidence summary and grade
- Risk flags and conflict warnings
- A feedback action prompt

The delivery manifest (`outbox/delivery_manifest.json`) is a machine-readable map of 29 dispatches to channels. It proves the system can hand off to an external delivery system (Telegram bot API, email service, Slack webhook) without additional processing.

Together, packets + manifest close the **"judges have to imagine distribution"** gap. The last mile before external channel integration is proven.

**How to add real feedback:** Run the feedback intake CLI after sharing a packet:

```bash
python3 packagers/feedback_intake.py --dispatch-id DSP-20260526-001 --status forwarded --note "Shared with Guyana investment partner"
```

This writes to `data/feedback/available.json`, which the next pipeline run reads via `feedback_loop.py apply` to adjust scores. The manual intake path means any channel (Telegram, email, Slack, in-person) can surface feedback — the dispatcher just needs a dispatch ID and a status.

---

## Step 9: Open `outbox/judge_brief.md`

**What this proves:** The full system architecture is documented — routing rationale, feedback mechanism, demo path, and future roadmap.

The brief includes:
- Complete routing rationale (10 signal kinds → 8 personas with *why* for each)
- The feedback loop mechanism with current active boosts
- The regional thesis pattern
- The editorial calendar design
- The judge demo path (this very document)

---

## Step 10: Open `dashboard.html`

**What this proves:** The operator console is a health view, not the product. It shows:
- Composite signal count (currently 25)
- Watcher health (6 sources tracked)
- Dispatch queue (29 dispatches)
- Dispatch Desk — delivery manifest and packet counts per persona
- Feedback loop status (4 events, active boosts visible)
- Regional thesis preview
- Why-now context
- Persona routing breakdown
- Routing Map — signal kind to persona mapping

The dashboard is what an operator uses to confirm the pipeline is alive. The *product* is the dispatch output, thesis, and routing.

---

## Summary: The Track 08 Claim

Caribbean Opportunity Dispatch is not a dashboard. It is a **continuous intelligence pipeline** that:

1. **Detects** signals from fragmented public data (6 watchers, 10+ sources)
2. **Judges** them with editorial enrichment (score bands, evidence grades, narrative titles)
3. **Routes** them to specific personas with recommended actions (31 dispatches, 8 personas)
4. **Distributes** them through appropriate channels (Email, Telegram, digest)
5. **Learns** from feedback (persistent state, decayed boosts, next-cycle adjustment)
6. **Synthesizes** a cross-cluster thesis connecting capital, risk, pipeline, and timing
7. **Contextualizes** every dispatch with seasonal and event awareness

The product output is the opportunity dispatch — a routed, actionable signal that tells a specific persona *what changed, why it matters now, and what to do next.*

---

*Generated: 2026-05-26*