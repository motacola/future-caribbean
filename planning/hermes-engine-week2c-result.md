# Hermes Engine Week 2C Result

Implemented Phase 2C: Live Cycle Theater with typed SSE and offline replay.

## Delivered

- Replaced the pipeline's plain-text SSE log with typed `source_check`, `signal_found`, `dispatch_routed`, and `cycle_complete` events.
- Hooked source events into the real `run_pipeline.sh` output and derived signal/dispatch events from each cycle's newly generated outbox.
- Added a shared live-event broadcaster so connected SSE clients receive events from both scheduled and on-demand pipeline cycles; the first live subscriber starts a cycle when the engine is idle.
- Added append-only daily replay history at `data/history/<YYYY-MM-DD>.jsonl`.
- Added `?replay=1` support using the latest local history file, with synthetic current-outbox events when no history exists.
- Added `/api/pipeline/status` as a graceful client fallback.
- Switched the server to `ThreadingHTTPServer` so an open SSE connection does not block other requests.
- Added `DISABLE_PIPELINE_LOOP=1` for offline/demo acceptance without an automatic startup cycle.
- Added the Signal Theater below the map with:
  - distinct source, signal, dispatch, and cycle-complete treatments
  - LIVE, REPLAY, and PAUSED states
  - pause/resume buffering
  - a maximum of 50 visible events
  - native `EventSource` and replay/status fallback
- Added the three requested stream/history/replay tests.

## Verification

- `python3 -m pytest -q`: **24 passed** (all existing + new tests)
- `python3 dashboard/generate.py --no-open`: **succeeded**
- `python3 -m py_compile pipeline_events.py server.py dashboard/generate.py`: **succeeded**
- Live `curl -N /api/pipeline/stream`: received real broadcast polling/completion source events while the pipeline ran; the completed cycle persisted signal, dispatch, and `cycle_complete` events.
- Replay `curl -N /api/pipeline/stream?replay=1`: emitted typed events from local JSONL history without running the pipeline.
- Browser acceptance:
  - Signal Theater rendered below the map.
  - Live events appeared.
  - Pause changed the state to `PAUSED` and button label to `Resume`.
  - Screenshot captured at `output/playwright/phase2c-theater.png`.

## Exit Criteria (all met)

1. ✅ `python3 -m pytest -q` passes (24/24 tests)
2. ✅ `curl -N localhost:8080/api/pipeline/stream` outputs typed SSE events (`source_check`, `signal_found`, `dispatch_routed`, `cycle_complete`)
3. ✅ Dashboard theater panel shows live events via native `EventSource` with pause/resume and mode indicator
4. ✅ `curl -N localhost:8080/api/pipeline/stream?replay=1` works without live network, streaming from `data/history/<today>.jsonl` with 10x timestamp compression

## History Persistence Verified

- After live pipeline cycle (cycle 46), `data/history/2026-06-10.jsonl` appended with 32 new events including `signal_found` for Guyana/Belize/Suriname, 14 `dispatch_routed`, and `cycle_complete`
- History file size grew from ~2.8KB to ~74KB demonstrating proper append-only daily logging
- Replay mode correctly reads and emits all event types from history

## Main Files

- `pipeline_events.py`
- `server.py`
- `dashboard/template.html`
- `dashboard.html`
- `tests/test_pipeline_stream.py`
- `data/history/2026-06-10.jsonl`
