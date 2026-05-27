# Caribbean Opportunity Dispatch

**Routed opportunity and risk dispatches from fragmented Caribbean public data.**

This is the product. The system architecture underneath is **Caribbean Signal OS** — a continuous multi-agent pipeline that watches public regional data, merges weak signals across sources, and packages them into routed dispatches for specific decision-makers.

**Track:** 08 — Intelligence, Media & Distribution Systems (Sapien + Polymath Buildathon)

---

## The Problem

Caribbean opportunity data is scattered across institutions, countries, and formats. That fragmentation delays investment decisions, procurement responses, resilience planning, founder matching, and public narrative.

Existing tools stop short:
- Data portals expose datasets but do not route decisions
- Newsletters explain market context but do not run a repeatable signal pipeline
- Dashboards show status but do not package channel-ready action
- Investor catalogues list opportunities but are not continuous watchers

This fills the **last mile between public regional data and acted-on opportunity**.

## The Product

Caribbean Opportunity Dispatch converts raw public data into five things per cycle:

- **Priority** — what matters this cycle
- **Routing** — who should receive it (persona + channel)
- **Action** — what decision it should trigger
- **Learning** — whether the dispatch produced a real response (feedback loop)
- **Distribution** — channel-ready packets with delivery manifest

The useful artifact is the dispatch, not the chart.

### Architecture (Caribbean Signal OS)

```
public data -> watchers -> normalized records -> reasoning merger -> composite signals
                                                                  -> opportunity dispatches (the product)
                                                                  -> regional thesis + why-now context
                                                                  -> feedback loop
                                                                  -> operator console (internal only)
```

## Key Artifacts (outbox/)

| Artifact | What it is |
|---|---|
| `outbox/opportunity_dispatches.md` | Routed dispatches with persona, channel, action, and feedback status |
| `outbox/regional_thesis.md` | Cross-cluster synthesis — investment, risk, pipeline, tourism in one narrative |
| `outbox/why_now.md` | Editorial calendar context — seasonal windows, procurement cycles, etc. |
| `outbox/judge_brief.md` | Full system intelligence brief with routing rationale |
| `outbox/feedback_review.md` | Feedback loop — what was forwarded, replied to, opened, or changed a decision |
| `outbox/channel_dispatch_log.md` | Distribution routing by channel |
| `outbox/dispatch_packets/*.md` | Persona-specific dispatch packets (action checklists, evidence, feedback options) |
| `outbox/delivery_manifest.json` | Channel-ready delivery manifest (one entry per dispatch) |
| `dashboard.html` | Internal operator console for pipeline health (not the product) |

## Data Sources

All sources are public, free, and require no API keys:

| Source | Method | Data |
|---|---|---|
| **World Bank** | REST API | 5 indicators × 13 Caribbean countries |
| **IDB Open Data** | CKAN API | 99 Caribbean datasets |
| **NOAA NWS** | REST API | Active weather alerts |
| **NDBC Buoys** | Tabular text | 6 buoys: wind, pressure, wave height |
| **CARICOM Statistics** | WordPress REST API | 126 datasets |
| **CDB** | RSS feed | Procurement notices, evaluation reports |

## Run

Full pipeline:

```bash
bash run_pipeline.sh
```

Individual steps:

```bash
python3 watchers/world_bank_poller.py
python3 mergers/cross_source_merger.py
python3 packagers/build_channel_outputs.py
python3 packagers/dispatch_packet_generator.py
python3 packagers/delivery_manifest.py
python3 dashboard/generate.py
```

Manual feedback intake:

```bash
python3 packagers/feedback_intake.py --dispatch-id DSP-20260526-001 --status forwarded --note "Forwarded to investor partner"
python3 packagers/feedback_loop.py apply
```

## Delivery

All watchers run on cron with noise-gated packaging and delivery. See `architecture/cron.md`. The system produces opportunities, not alerts — every dispatch names a specific persona, a channel, an action, and a decision it supports. The dispatch packet and delivery manifest layers prove the last mile before external channel integration.

## Deployment

For static hosting (Netlify, GitHub Pages, etc.):

1. Run `bash run_pipeline.sh` to generate all artifacts
2. Deploy `dashboard.html`, `outbox/*.md`, and `assets/` as static files
3. No build step needed — all HTML/Markdown is self-contained
4. Cron jobs on the backend continue data collection independently
