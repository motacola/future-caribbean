# Future Caribbean Application Draft — Caribbean Opportunity Dispatch

## Track

**10 — Open Track**

## Project name

Caribbean Opportunity Dispatch

## One-liner

Caribbean Opportunity Dispatch turns fragmented Caribbean public data into decision-ready routes: what changed, who should act, what they should do next, and how feedback changes the next cycle.

## Category

Agentic market coordination infrastructure for fragmented Caribbean economies.

## Problem

Public data about Caribbean economies already exists. World Bank indicators, IDB datasets, CDB procurement notices, CARICOM statistics, NOAA alerts, marine buoys — all free, all published regularly. But it never reaches the people who could act on it in time.

Investors miss early signals because they are buried across ten different portals. Founders miss procurement windows because no one connects the notice to their capability. Policy teams react late because they lack a continuous reading. The gap is not data availability. The coordination layer is missing.

Caribbean Opportunity Dispatch fills that gap — turning fragmented public data into routed decision clusters with evidence, persona-specific actions, and a feedback loop that learns what gets acted on.

## Solution

Caribbean Opportunity Dispatch is a live Dispatch Desk that converts fragmented public data into routed decision clusters.

Each cycle:

- watcher agents pull public regional data
- a merger combines weak signals across countries and sources
- packagers score, narrate, and contextualize the signals
- the Dispatch Desk groups them into decision clusters
- persona routes assign each signal to the right user and channel
- delivery packets and a manifest prove distribution readiness
- feedback changes ranking in the next cycle

The product is not the dashboard. The product is the decision route: signal -> persona -> action -> feedback.

## Why Open Track

This is not a sector-specific app. Finance, disaster risk, food systems, ocean systems, tourism, and procurement are signal domains inside the system.

Open Track is the right fit because Caribbean Opportunity Dispatch is cross-sector coordination infrastructure. It helps fragmented markets move from public signal to economic action faster.

## Users

- Diaspora investors screening where to investigate capital deployment
- Regional founders/operators deciding where to pursue market entry or partnerships
- Ecosystem builders routing opportunities to the right founders, funders, or partners
- Procurement watchers tracking CDB/IDB project windows
- Policy/media teams identifying timely regional narratives
- Tourism/logistics teams watching demand, climate, and operational signals

## Current Working System

The system already produces real outputs:

- Dispatch Desk with decision clusters
- persona-specific dispatch packets
- delivery manifest for channel handoff
- regional thesis
- why-now context
- feedback review
- headless query CLI
- live dashboard/operator console

Current data sources are public and require no API keys:

- World Bank
- IDB Open Data
- NOAA/NWS
- NDBC marine buoys
- CARICOM Statistics
- CDB procurement feed

## AI / Agentic Components

- Watcher agents gather public data by source family
- Merger logic turns raw source updates into composite regional signals
- Packaging agents enrich signals with evidence grade, confidence, why-now context, risk flags, and persona routes
- Feedback loop adjusts future ranking based on opens, forwards, replies, ignores, and decision-change markers
- Analyst rail / query CLI lets users interrogate the current cycle without reading every artifact

## Why Caribbean / Why Now

The Caribbean is a perfect testbed for this problem: many small markets, high fragmentation, regional institutions, diaspora capital, climate exposure, tourism dependence, procurement-driven development, and cross-border opportunity flow.

Faster signal routing can improve how capital, operators, media, and institutions respond to the region's real economy.

## Five-Year Potential

Caribbean Opportunity Dispatch can become a regional intelligence and coordination layer for investors, operators, institutions, and ecosystem builders.

In five years it could support:

- live regional opportunity routing
- capital and procurement watchlists
- sector-specific dispatch desks
- institution and investor intelligence briefs
- API-based delivery into Telegram, WhatsApp, Slack, email, and CRM tools
- expansion from the Caribbean to other fragmented regional markets

## Demo Path

1. Run `bash run_pipeline.sh`
2. Open `dashboard.html`
3. Show the Dispatch Desk decision clusters
4. Open `outbox/dispatch_desk.md`
5. Open a persona packet, e.g. `outbox/dispatch_packets/diaspora_investor.md`
6. Open `outbox/delivery_manifest.json`
7. Open `outbox/feedback_review.md`
8. Use the Ask the Dispatch Desk rail or `python3 agent/query.py ask "show investor actions"`

## Closing Claim

Caribbean Opportunity Dispatch compresses the time between public signal and economic action.
