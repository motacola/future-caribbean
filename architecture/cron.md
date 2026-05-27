# Caribbean Signal OS Schedule

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

## Success Signal

The system is healthy when:

- source data/*/latest.json files update on cadence
- data/composite/latest.json contains cross-source signals
- outbox/investor_brief.md, outbox/telegram_digest.md, and outbox/diaspora_post.md regenerate
- distribution sends only meaningful deltas
- feedback metrics identify which signals spread or changed a decision
