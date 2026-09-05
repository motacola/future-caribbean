# Abeng - Uniqueness and Improvement Plan

Date: 2026-05-26

## Executive Verdict

There does not appear to be an obvious existing product that does the full Track 08 loop for the Caribbean:

    public data -> cross-country signal -> narrative packaging -> channel delivery -> recipient action -> feedback learning

But there are many products that cover pieces of it:

- statistical portals
- investment catalogues
- procurement/tender tools
- diaspora investor networks
- newsletters and political/economic briefings
- Caribbean SEO/trend platforms
- country brief platforms

That means the product can be unique, but only if it does not collapse into one of those existing categories.

The danger zone is:

    "AI-generated Caribbean investment newsletter"

That is not enough.

The unique product wedge should be:

    Abeng.

A continuous Track 08 routing layer that turns fragmented Caribbean public data into opportunity dispatches for regional operators and diaspora capital networks, then learns which dispatches trigger follow-up.

## Competitor / Adjacent Landscape

### 1. Institutional Data Portals

Examples checked:
- CARICOM Statistics
- IDB / Latin Macro Watch / CaribData references
- World Bank / IDB / CDB public data sources

What they do:
- publish indicators, datasets, dashboards, project pages, and statistics
- provide raw or semi-structured data for researchers, policymakers, and analysts

What they do not do:
- turn data into channel-native action dispatches
- decide who should receive a signal
- track whether anyone acted
- package the same signal differently for diaspora investors, founders, operators, or media

Implication:
Abeng should position these as inputs, not competitors.

### 2. Investment Catalogues and Promotion Sites

Examples checked:
- Caribbean Export Investment Catalogue
- investment-promotion content around Caribbean Investment Forum

What they do:
- present curated project opportunities
- showcase investment-ready ventures or sectors
- connect global investors with prepared opportunities

What they do not do:
- continuously monitor changing public data
- detect fresh market signals
- compare opportunities across countries dynamically
- learn from investor/operator feedback

Implication:
Abeng should not try to be a static investment catalogue. It should be the early-warning and routing layer that says, "this market/opportunity deserves attention now."

### 3. Diaspora / Angel Investor Networks

Examples checked:
- Caribbean Diaspora Angel Investor Network via VC4A
- Caribbean Angel Investment Network
- Caribbean Venture Collective search result

What they do:
- connect investors and entrepreneurs
- provide network/community infrastructure
- support startup fundraising and investor discovery

What they do not do:
- generate public-data-backed regional opportunity signals
- explain why a country/sector is heating up this week
- produce cross-country evidence packages
- route opportunities based on live signals

Implication:
These could be recipients or partners in the product story. Abeng can feed better signals into these networks.

### 4. Procurement and Tender Tools

Examples checked:
- Procur
- TenderTrack
- CDB Procurement pages

What they do:
- aggregate tenders/procurement notices
- send notifications
- provide search, category tagging, summaries, or pursuit workflows
- in Procur's case, use AI for tender summaries, compliance matrices, proposal support, and pursuit pipelines

What they do not do:
- cover the broader market-signal layer beyond procurement
- synthesize macro/FDI/weather/procurement/news context into one opportunity thesis
- route signals to diaspora capital or ecosystem audiences
- connect procurement signals to wider market momentum

Implication:
This is the closest workflow threat. We should not compete head-on as "better procurement alerts." Instead:
- use procurement as one dispatch type
- connect procurement to broader country/sector momentum
- generate operator/investor action around that momentum

### 5. Caribbean Market Intelligence / Country Briefing Tools

Examples checked:
- CaribTrends
- Carib Insights
- Caribbean Council's Caribbean Insight

What they do:
- publish country briefs, trend insights, SEO/search demand, business/political analysis, newsletters
- help users understand countries, dates, taxes, trends, or market demand

What they do not do:
- operate as a multi-agent pipeline tied to Track 08's full loop
- route each signal into an action queue
- capture opened/forwarded/replied/decision-changed feedback
- make distribution and next-cycle learning central

Implication:
This is the category Abeng will be mistaken for unless the demo visibly shows dispatch and feedback.

## What Is Actually Unique

The defensible uniqueness is not "Caribbean data" or "AI summaries."

The unique wedge is:

    A continuous Caribbean public-data-to-action routing layer.

More specifically:

1. Cross-source signal detection
   Combines World Bank, IDB, CDB/procurement, weather/marine, CARICOM/Tier2 sources, and later news/social/search signals.

2. Cross-country regional view
   Makes the Caribbean legible as one connected market rather than isolated country pages.

3. Persona-specific packaging
   Same signal becomes different outputs for:
   - diaspora investor
   - regional founder/operator
   - procurement watcher
   - ecosystem builder
   - media/diaspora audience

4. Dispatch object as core product
   Every signal becomes a routed opportunity dispatch with recipient, action window, next step, evidence, channel, and feedback prompt.

5. Feedback loop
   Tracks which signals are opened, forwarded, replied to, or marked as decision-changing, then changes the next cycle.

6. Track 08-native narrative
   Converts data into media/distribution assets, not just internal analytics.

## Product Strategy

### Product Name

Architecture:

    Abeng

Product:

    Abeng

Alternative if we want a less salesy name:

    Caribbean Market Dispatch

Recommended pitch:

    Abeng turns fragmented Caribbean public data into routed, decision-grade opportunity signals for regional operators and diaspora capital networks.

### Primary User

Do not say "everyone."

Primary:

    Regional founders/operators and diaspora investors who need to know where to act next.

This is a two-sided product:
- Regional actors have opportunities, procurement lanes, market movement, risks, or needs.
- Diaspora investors/ecosystem actors have attention, capital, networks, advice, and follow-up capacity.

Secondary:
- accelerators
- investor networks
- chambers of commerce
- trade/export agencies
- media/newsletter operators
- policy analysts

### Core Use Case

A public signal appears.

Normally, it sits in a PDF, portal, dashboard, or dataset until someone notices it.

Abeng detects it, enriches it, chooses the audience, generates a dispatch, sends it through a channel, and records whether it caused follow-up.

Example:

    Guyana FDI velocity + CDB/IDB project activity + regional growth signal
    -> Dispatch to diaspora investor + regional operator
    -> "Validate Guyana supplier/procurement lane this week"
    -> Telegram/WhatsApp/email-ready output
    -> feedback: forwarded/replied/intro requested
    -> next cycle ranks similar capital-momentum signals higher

## Why This Could Win

It matches Track 08 exactly:

- Data: public datasets across countries
- Signal: cross-source and cross-country pattern detection
- Packaging: investor/operator/diaspora/media variants
- Distribution: Telegram/WhatsApp/email-ready outputs
- Action: dispatch queue with next steps and owners
- Capital: diaspora/investor follow-up and procurement/dealflow routing
- Feedback: learning what spreads and what changes decisions

It also matches the homepage:
- reduces fragmentation
- compresses T
- creates coordination infrastructure
- operates continuously
- can become a company

## Why It Could Lose

It loses if judges see:
- a dashboard
- a markdown report generator
- an AI newsletter
- generic "regional intelligence"
- claims about moving capital without a capital-adjacent workflow
- too many users and no clear buyer
- no actual or simulated distribution/feedback

## Improvement Plan

### Phase 1 - Make The Product Object Real

Build the opportunity dispatch layer.

Add:

    packagers/opportunity_dispatch.py
    config/recipients.json
    outbox/opportunity_dispatches.json
    outbox/opportunity_dispatches.md

Dispatch fields:

- dispatch_id
- signal_id
- title
- country_or_cluster
- signal_kind
- persona
- recipient_type
- decision_to_influence
- recommended_action
- action_window
- channel
- evidence
- confidence
- risk_flags
- feedback_prompt
- delivery_status
- feedback_status
- next_cycle_effect

Acceptance criteria:
- At least 5 dispatches generated per pipeline run.
- Each dispatch has a specific persona and next action.
- No dispatch says only "monitor" unless it explains what would trigger escalation.

### Phase 2 - Add Recipient Rules

Create explicit routing logic.

Example rules:

- FDI velocity / macro opportunity -> diaspora investor, ecosystem builder, founder/operator
- Procurement/project pipeline -> regional operator, procurement watcher, founder/operator
- Tourism demand/weather risk -> tourism/logistics operator
- Vulnerability/risk conflict -> investor risk validation, policy/media context
- Multi-country trend -> diaspora audience, media channel, investor brief

Acceptance criteria:
- The system can explain why a signal went to a persona.
- Judge brief includes "routing rationale."
- Investor/operator digest contains different wording from public/diaspora output.

### Phase 3 - Prove Distribution

Add delivery artifacts even if live external sending is not enabled.

Add:

    outbox/channel_dispatch_log.md
    data/feedback/delivery_log.jsonl

Each generated dispatch should have:
- target channel
- sent/simulated status
- timestamp
- recipient persona
- message preview
- feedback request

Acceptance criteria:
- Demo shows a signal was routed to a channel.
- The artifact looks like delivery, not just a file export.
- If real Telegram delivery is used, include message IDs. If simulated, label it clearly as demo simulation.

### Phase 4 - Feedback Review and Learning

Add:

    outbox/feedback_review.md

Review:
- opened
- forwarded
- replied
- decision_changed
- ignored
- next-cycle adjustment

For demo, seed plausible feedback events:
- investor forwarded Guyana dispatch
- operator replied to procurement dispatch
- diaspora post ignored due to vague headline
- risk-conflict signal marked useful

Acceptance criteria:
- The next cycle can say why ranking or wording changed.
- Judge can see the feedback agent loop without needing an external account.

### Phase 5 - Make The Narrative Less Generic

Add calendar/context and cross-cluster synthesis.

Add:

    config/editorial_calendar.json

Inputs:
- hurricane season
- tourism cycles
- procurement windows
- regional events
- buildathon/judging timeline
- budget/IMF/review windows where public data supports it

Add cross-cluster thesis:

    "Capital momentum is strongest where FDI velocity, project pipeline, and low risk conflict overlap."

Acceptance criteria:
- Every lead dispatch answers "why now?"
- The system produces one regional thesis per cycle.
- The lead story is no longer just the highest score.

### Phase 6 - Demo Rewrite

New demo order:

1. Start with the problem:
   "Public signals die in portals and PDFs. The delay between signal and follow-up is economic drag."

2. Run pipeline:
   bash run_pipeline.sh

3. Show opportunity dispatch queue:
   outbox/opportunity_dispatches.md

4. Show one dispatch:
   - who it is for
   - what changed
   - why now
   - what action to take
   - what evidence supports it
   - where it was routed

5. Show channel output:
   Telegram/WhatsApp/email-ready dispatch

6. Show feedback review:
   opened/forwarded/replied/decision_changed

7. Show judge brief last:
   system architecture and Track 08 mapping

Avoid opening the dashboard first.

## Concrete Build Order

1. Implement packagers/opportunity_dispatch.py.
2. Add config/recipients.json.
3. Update packagers/build_channel_outputs.py to call the dispatch generator.
4. Generate outbox/opportunity_dispatches.json/md.
5. Generate outbox/feedback_review.md.
6. Add demo feedback seed data.
7. Update deliverables/demo-script.md.
8. Update deliverables/submission-positioning.md.
9. Run python3 -m py_compile and bash run_pipeline.sh.
10. Review judge/investor/dispatch outputs for product clarity.

## Positioning To Use

One-liner:

    The Caribbean's public-data-to-opportunity dispatch layer.

Short pitch:

    Abeng turns fragmented Caribbean public data into routed opportunity signals for regional operators and diaspora investors, then learns which signals trigger follow-up.

Judge framing:

    This is a Track 08 system: continuous watcher agents detect cross-country signals, packaging agents turn them into channel-native dispatches, distribution agents route them to real user personas, and feedback agents learn what spreads, what is trusted, and what changes decisions.

What not to say:

    "AI dashboard"
    "market intelligence newsletter"
    "regional data analysis tool"
    "investment advice"
    "we move capital"

What to say:

    "We route public signals into follow-up."
    "We shorten time from signal to action."
    "We turn fragmented public data into dispatches for people who can act."
    "Capital is not moved inside the app; capital attention and diligence are routed."

