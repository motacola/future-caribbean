# Hermes Build Brief - Phase 5 Action Proof Layer

Rob/Codex has completed the strategy pass in `planning/phase5-action-proof-plan.md`.

Your job is implementation only.

## Read First

- `planning/phase5-action-proof-plan.md`
- `outbox/opportunity_dispatches.json`
- `packagers/opportunity_dispatch.py`
- `packagers/feedback_loop.py`
- `dashboard/generate.py`
- `run_pipeline.sh`

## Build

1. Add a dispatch packet generator that writes persona-specific packets under `outbox/dispatch_packets/`.
2. Generate `outbox/delivery_manifest.json` from `outbox/opportunity_dispatches.json`.
3. Add `packagers/feedback_intake.py` for CLI feedback capture into `data/feedback/available.json`.
4. Wire packet/manifest generation into `run_pipeline.sh` after opportunity dispatch generation.
5. Update `dashboard/generate.py` with a compact Dispatch Desk section.
6. Update README/demo/submission docs to include packets, manifest, and feedback intake.

## Constraints

- Do not deploy externally.
- Keep files simple and stdlib-only.
- Do not remove existing outbox artifacts.
- Do not mutate persistent feedback state during normal pipeline runs except existing feedback loop behavior.
- Use generated artifacts as proof; avoid hand-written fake examples.

## Validation

Run:

```bash
python3 -m py_compile packagers/*.py dashboard/generate.py
bash run_pipeline.sh
python3 - <<'PY'
import json, pathlib
root = pathlib.Path('.')
dispatches = json.loads((root/'outbox/opportunity_dispatches.json').read_text())['dispatches']
manifest = json.loads((root/'outbox/delivery_manifest.json').read_text())['deliveries']
packets = list((root/'outbox/dispatch_packets').glob('*.md'))
print(len(dispatches), len(manifest), len(packets))
assert len(dispatches) == len(manifest)
assert len(packets) >= 5
PY
python3 packagers/feedback_intake.py --dispatch-id DSP-TEST --status forwarded --note "judge demo smoke"
python3 packagers/feedback_loop.py apply
rg -n "FDI surge \(WB\) \+ supporting context|Summary: FDI surge|FDI surge \(WB\)|Unknown persona|No action recorded" outbox dashboard.html packagers README.md deliverables -S
```

The final `rg` should return no matches. If it returns matches, fix them.

Final summary must list changed files, validation commands, and any risks.

