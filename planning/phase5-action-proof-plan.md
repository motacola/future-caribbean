# Phase 5 Plan - Action Proof Layer

## Why This Phase Exists

Phase 4 made the product legible. Phase 5 needs to make it harder for judges to dismiss the system as "good packaging around data."

The remaining weakness is action proof:

- Dispatches are generated, but the demo still asks judges to imagine delivery.
- Feedback exists, but most events are seeded/simulated.
- The operator console proves the pipeline is alive, but not that a recipient can act from the artifact.

The next phase should prove the last mile:

> A regional signal becomes a recipient-specific dispatch packet, reaches a named persona/channel, and can receive structured feedback that affects the next cycle.

## Product Target

Build a lightweight **Dispatch Desk** layer:

- recipient-specific packet files
- channel-ready delivery manifest
- feedback intake path
- demo evidence page

This does not need external sending yet. It needs to demonstrate that distribution and feedback are real system surfaces, not prose.

## Build Scope For Hermes

### 1. Generate Recipient Dispatch Packets

Create a packager that reads `outbox/opportunity_dispatches.json` and writes:

- `outbox/dispatch_packets/diaspora_investor.md`
- `outbox/dispatch_packets/founder_operator.md`
- `outbox/dispatch_packets/ecosystem_builder.md`
- `outbox/dispatch_packets/policy_media.md`
- `outbox/dispatch_packets/procurement_watcher.md`
- `outbox/dispatch_packets/regional_operator.md`

Each packet should include:

- persona name and decision job
- top routed dispatches for that persona
- action checklist
- feedback options
- source/evidence references

### 2. Create Delivery Manifest

Write `outbox/delivery_manifest.json` with one object per dispatch:

- dispatch_id
- title
- persona_key
- persona_label
- channel
- delivery_status
- action_window
- feedback_prompt
- target artifact path

This becomes the system proof that dispatches are ready for channel delivery.

### 3. Add Feedback Intake

Add a small CLI/script:

- `packagers/feedback_intake.py`

It should accept:

```bash
python3 packagers/feedback_intake.py --dispatch-id DSP-... --status forwarded --note "..."
```

It should append/merge into:

- `data/feedback/available.json`

Then the existing `packagers/feedback_loop.py apply` path can consume it.

### 4. Update Pipeline

Wire after `opportunity_dispatch.py`:

- generate dispatch packets
- generate delivery manifest

Do not break the existing feedback loop.

### 5. Update Operator Console

Add a compact section:

- Dispatch Desk
- packet count
- manifest count
- top packet links
- feedback intake hint

### 6. Update Demo Docs

Update:

- `deliverables/judge-demo-walkthrough.md`
- `README.md`
- `deliverables/submission-positioning.md`

The demo should now include:

1. opportunity dispatches
2. recipient packet
3. delivery manifest
4. feedback intake example
5. regional thesis
6. operator console

## Acceptance Criteria

- `bash run_pipeline.sh` writes dispatch packets and delivery manifest.
- Each major persona has a readable packet file.
- `delivery_manifest.json` has the same dispatch count as `opportunity_dispatches.json`.
- `feedback_intake.py` can write one test event to `data/feedback/available.json`.
- Running `feedback_loop.py apply` after intake includes that available feedback without crashing.
- `dashboard.html` shows Dispatch Desk state.
- Compile checks pass.
- Old boilerplate search remains zero.

## Creative Direction

This should feel operational, not decorative:

- "Here is the packet sent to diaspora investors."
- "Here is the manifest of what would be delivered."
- "Here is how feedback enters the next cycle."

Judges should no longer need to imagine the distribution layer.

