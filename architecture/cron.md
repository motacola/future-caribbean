# Abeng Schedule

The production loop should run continuously and distribute channel-ready signals, not static reports.

## Shell Cron

```cron
15 7 * * * cd /Users/christopherbelgrave/clawd/projects/future-caribbean && bash run_pipeline.sh >> data/pipeline.log 2>&1
```

## OpenClaw Cron Intent

Use OpenClaw cron for packaging and distribution once the watcher output is useful:

- schedule: daily morning for market pulse, faster cadence for weather/marine alerts
- task: run watchers, merger, packaging agents, and distribution deltas
- delivery: Telegram/SMS for urgent operational alerts, email/Telegram for investor briefs, social/WhatsApp-ready text for diaspora narratives
- feedback: append distribution outcomes to outbox/feedback_queue.json or a future event store

## User-facing presentation

The primary user/judge-facing surface is the **Dispatch Desk**: `outbox/dispatch_desk.md` plus the top section of `dashboard.html`. It groups repeated persona routes into decision clusters so Open Track reviewers can see the complete coordination chain: fragmented public data → agentic signal pipeline → routed decisions → feedback → faster regional action.

Each full pipeline cycle writes:

- `outbox/dispatch_desk.md` / `.json` — product surface and machine-readable clusters
- `outbox/telegram_brief.md` — compact notification adapter pointing back to the desk
- `outbox/dispatch_packets/*.md` — persona-ready delivery packets
- `outbox/delivery_manifest.json` — channel handoff manifest

Cron wrappers should run `distributors/delta_outbox.py` once after the pipeline completes. That delta step hashes `telegram_brief.md` and prints it only when changed; empty stdout means Hermes sends nothing. This preserves low-noise delivery without making Telegram the product.

Interaction model:

- User or judge opens the Dispatch Desk first for the decision clusters.
- The dashboard **analyst rail** ("Ask the Dispatch Desk") lets users interrogate the cycle: explain the lead signal, show investor actions, ask what changed, drill into a country, or draft an investor note. All answers are deterministic and cite local artifacts.
- The headless query CLI (`agent/query.py`) exposes the same logic for CLI, Telegram, and future API clients.
- Telegram/email notify that decision routes changed and summarize the top clusters.
- Persona packets show what each recipient would receive.
- Feedback can be recorded with `packagers/feedback_intake.py` and affects next-cycle ranking through `feedback_loop.py`.
- `dashboard.html` combines the Dispatch Desk product view with lower operator/audit sections for pipeline health.

The agent/query layer is intentionally separate from cron. Cron produces artifacts; `agent/query.py` and the dashboard analyst rail interrogate those artifacts. Future headless services should call the same query functions rather than reimplementing interpretation.

## Success Signal

The system is healthy when:

- source data/*/latest.json files update on cadence
- data/composite/latest.json contains cross-source signals
- outbox/dispatch_desk.md, outbox/opportunity_dispatches.json, outbox/dispatch_packets/, outbox/delivery_manifest.json, and outbox/telegram_brief.md regenerate
- outbox/telegram_brief.md stays under Telegram's 4096 character limit
- distribution sends only meaningful deltas
- feedback metrics identify which signals spread or changed a decision
