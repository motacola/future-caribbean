# Flue Harness — Level 1

This repo now has a thin Flue wrapper around the existing Abeng Python pipeline.

The Python pipeline remains the source of truth:

- `bash run_pipeline.sh` generates watcher/merger/packager outputs.
- `agent/query.py` answers deterministic questions over generated artifacts.
- `outbox/dispatch_desk.json` is the canonical machine-readable dispatch desk artifact.

Flue adds a programmable harness layer:

- workflow endpoint: `ask-dispatch`
- workflow endpoint: `run-cycle`
- workflow endpoint: `record-feedback`
- workflow endpoint: `generate-brief`
- workflow endpoint: `list-artifacts`
- workflow endpoint: `open-notebook-sync`
- agent endpoint: `dispatch-desk`
- health route: `/health`

## Install

```bash
npm install
```

## Local CLI usage

Ask the current dispatch cycle:

```bash
npx flue run ask-dispatch --target node --payload '{"question":"explain lead"}'
npx flue run ask-dispatch --target node --payload '{"question":"what changed this cycle"}'
```

Run a full pipeline cycle through Flue:

```bash
npx flue run run-cycle --target node --payload '{}'
```

Generate an audience-specific brief:

```bash
npx flue run generate-brief --target node --payload '{"audience":"investor","channel":"memo","maxClusters":3}'
npx flue run generate-brief --target node --payload '{"audience":"operator","channel":"telegram","maxClusters":2}'
```

List or read generated artifacts:

```bash
npx flue run list-artifacts --target node --payload '{}'
npx flue run list-artifacts --target node --payload '{"path":"outbox/judge_brief.md","maxBytes":12000}'
```

Record operator feedback for the next cycle:

```bash
npx flue run record-feedback --target node --payload '{"dispatchId":"DSP-20260603-021","status":"forwarded","note":"Shared with investor lead","source":"operator"}'
```

Check or push the current cycle into local Open Notebook:

```bash
npx flue run open-notebook-sync --target node --payload '{"action":"status"}'
# If Open Notebook auth is enabled, run the Flue process with OPEN_NOTEBOOK_TOKEN or OPEN_NOTEBOOK_PASSWORD set.
npx flue run open-notebook-sync --target node --payload '{"action":"push-cycle","notebookName":"Future Caribbean Dispatch"}'
```

Build the Flue Node server:

```bash
npx flue build --target node
```

## Local HTTP server

```bash
PORT=3593 node dist-flue/server.mjs
```

Health:

```bash
curl http://127.0.0.1:3593/health
```

Invoke a workflow and wait for the result:

```bash
curl 'http://127.0.0.1:3593/workflows/ask-dispatch?wait=result' \
  -H 'Content-Type: application/json' \
  -d '{"question":"what changed this cycle"}'
```

## Optional auth

Set `FLUE_API_TOKEN` to require Bearer auth on agents, workflows, and run routes:

```bash
FLUE_API_TOKEN='choose-a-secret' PORT=3593 node dist-flue/server.mjs
curl 'http://127.0.0.1:3593/workflows/ask-dispatch?wait=result' \
  -H 'Authorization: Bearer ***' \
  -H 'Content-Type: application/json' \
  -d '{"question":"explain lead"}'
```

When `FLUE_API_TOKEN` is unset, local development routes are open.

## What this is not yet

This is not a replacement for the existing Python web server or dashboard. It is a Level 1 harness wrapper that proves the pipeline can be invoked and queried as structured Flue workflows.

Next Level 2 candidates:

- `record-feedback` workflow wrapping `packagers/feedback_intake.py`
- `generate-brief` workflow for investor/WhatsApp/Telegram/policy outputs
- Open Notebook source-ingestion/query tool
- deployment wiring as a sidecar service or route integration
