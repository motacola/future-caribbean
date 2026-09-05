# Phase 4 Plan - Judge-Ready Product Surface

## Strategic Position

The product is **Abeng**. Judges should not have to infer the product from pipeline internals. The first thing they should understand is:

> Abeng turns fragmented Caribbean public data into routed opportunity and risk dispatches for the people who can act on them.

The winning frame is not "we built a dashboard" or "we summarize regional data." The winning frame is:

1. Caribbean opportunity data is scattered across institutions, countries, and formats.
2. That fragmentation delays investment, procurement response, resilience planning, founder matching, and public narrative.
3. This system shortens the gap between a regional signal appearing and the right person acting on it.
4. It learns from feedback, so the product improves based on what gets opened, forwarded, replied to, or changes a decision.

## Primary User

The primary user is a **regional opportunity operator**:

- diaspora investor screening Caribbean market entry
- founder/operator deciding where to expand
- ecosystem builder routing founders and capital
- procurement watcher scanning public-sector project windows
- policy/media operator turning data into trusted distribution

This is not for casual readers. It is for people who already need to make decisions but do not have the time or infrastructure to monitor six fragmented public data systems.

## Core Value

The product creates value by converting raw public data into four things:

- **priority**: what matters this cycle
- **routing**: who should receive it
- **action**: what decision it should trigger
- **learning**: whether the dispatch produced a real response

The useful artifact is the dispatch, not the chart.

## Competition Gap

Existing institutions and tools mostly stop at one of these layers:

- data portals expose datasets but do not route decisions
- newsletters explain market context but do not run a repeatable signal pipeline
- procurement tools list tenders but do not connect them to wider market context
- dashboards show status but do not package channel-ready action
- investor catalogues list opportunities but are not continuous public-data watchers

The gap this fills is the **last mile between public regional data and acted-on opportunity**.

## Phase 4 Build Scope

Hermes should focus on build/deployment work only. The target is a judge-ready product surface that makes the loop obvious in under two minutes.

### 1. Reposition Docs Around the Product

Update:

- `README.md`
- `deliverables/demo-script.md`
- `deliverables/submission-positioning.md`
- `architecture/editorial-layer.md` if needed

Required changes:

- Lead with **Abeng** as both the product and the system name.
- Replace stale references to `feedback_queue.json` as the main feedback artifact with the current dispatch + persistent feedback loop:
- `outbox/opportunity_dispatches.md`
- `outbox/regional_thesis.md`
- `outbox/why_now.md`
- `outbox/feedback_review.md`
- `data/feedback/state.json`
- `data/feedback/current_boosts.json`
- Update demo flow to match `outbox/judge_brief.md`.
- Make the product value legible without reading source code.

### 2. Upgrade Dashboard Into Operator Console

Update `dashboard/generate.py` and generated `dashboard.html`.

The console should show:

- product name and one-line purpose
- live pipeline status
- current regional thesis
- why-now context
- top opportunity dispatches
- persona routing counts
- feedback loop state
- watcher/source health

The dashboard must clearly say it is an **operator console**, not the product itself.

### 3. Add Judge Walkthrough Artifact

Create:

- `deliverables/judge-demo-walkthrough.md`

It should be a tight script:

1. Run the pipeline.
2. Show opportunity dispatches.
3. Show regional thesis.
4. Show why-now context.
5. Show feedback review / current boosts.
6. Show operator console last.
7. Close with why this fits Track 08.

### 4. Deployment Prep

Prepare the project for simple static deployment:

- ensure `dashboard.html` is current after pipeline run
- add clear deploy notes for static hosting
- avoid adding secrets or paid infrastructure
- do not deploy externally unless Chris explicitly says to deploy

## Creative Direction

The visual tone should feel like a regional operations desk:

- useful, dense, legible
- signal-first, not decorative
- restrained Caribbean cues, not tourist branding
- clear urgency levels and routing labels
- no fake marketing hero

Use product language:

- Dispatch
- Signal
- Route
- Decision
- Feedback
- Cycle
- Thesis
- Why now

Avoid vague language:

- insights
- AI-powered
- dashboard
- ecosystem platform
- revolutionary

## Acceptance Criteria

Phase 4 is done when:

- A judge can answer "what is the product?" within 15 seconds.
- A judge can see how Track 08's Data -> Signal -> Packaging -> Distribution -> Action -> Capital chain is implemented.
- The dashboard/operator console reflects the current Phase 3 system, not the older watcher-only version.
- The demo script points at real artifacts that exist and are generated by `bash run_pipeline.sh`.
- Compile checks pass for touched Python files.
- Full pipeline runs cleanly.
- No old boilerplate language returns.

