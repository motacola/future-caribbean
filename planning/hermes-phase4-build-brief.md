# Hermes Build Brief - Phase 4

You are Hermes in the Future Caribbean Phase 4 build lane.

Chris wants speed. Rob/Codex owns strategy, creative direction, and verification. Hermes owns build/deployment implementation.

Work in /Users/christopherbelgrave/clawd/projects/future-caribbean.

Do not deploy externally unless Chris explicitly says to deploy.

## Read First

- planning/phase4-judge-ready-product-plan.md
- outbox/judge_brief.md
- outbox/regional_thesis.md
- outbox/why_now.md
- outbox/opportunity_dispatches.md
- README.md
- deliverables/demo-script.md
- deliverables/submission-positioning.md
- dashboard/generate.py

## Build Scope

1. Reposition docs around the actual product: Caribbean Opportunity Dispatch. Keep Caribbean Signal OS as the underlying architecture/system.
2. Update stale demo/submission references so the judge flow points to the current Phase 3 artifacts: opportunity dispatches, regional thesis, why-now, feedback review, judge brief, dashboard last.
3. Upgrade dashboard/generate.py so dashboard.html becomes a judge-ready operator console showing product purpose, current regional thesis, why-now context, top dispatches, persona routing counts, feedback loop state, and source health.
4. Add deliverables/judge-demo-walkthrough.md with a tight 2-minute walkthrough.
5. Add static deployment notes if missing. Do not deploy externally yet.

## Creative Direction

Dense, utilitarian regional operations desk. Signal-first. Restrained. No marketing hero. No tourist branding.

## Acceptance Gates

- python3 -m py_compile on touched Python files
- bash run_pipeline.sh
- old boilerplate search must return zero for:
- FDI surge (WB) + supporting context
- Summary: FDI surge
- FDI surge (WB)

Final summary must list changed files, validation commands, and unresolved risks.

