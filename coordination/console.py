#!/usr/bin/env python3
"""Local operator console for the coordination closed loop.

Runs on localhost (where the repo is writable). The Abeng site is
static + serverless, and Vercel's filesystem is read-only at runtime, so
outcomes are recorded HERE, then committed + deployed (the same
artifact-commit convention the rest of the pipeline uses).

Usage:
  python3 coordination/console.py [--port 8765]

Then open http://localhost:8765 — pick an intervention, click an outcome
(supplier validated / intro accepted / blocked by logistics), or submit
evidence / verify. Each action persists to data/intervention_state.json,
re-runs the engine, and regenerates outbox/. The console then prints the
exact git commit command to ship the change.
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]


def _load_mods():
    try:
        from coordination import interventions, engine
    except ImportError:
        sys.path.insert(0, str(ROOT))
        from coordination import interventions, engine  # type: ignore
    return interventions, engine


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _regenerate(interventions, engine) -> None:
    engine.run(ROOT)


def _commit_hint() -> str:
    return (
        "git add data/intervention_state.json outbox/coordination_opportunities.json "
        "data/coordination/graph.json && git commit -q -m \"op: coordination outcome update\" "
        "&& git push && gh pr create --fill --head coord-op-$(__import__('time').strftime('%Y%m%d%H%M')) "
        "--base main"
    )


HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Coordination Console</title>
<style>
  :root { --bg:#F4EBDD; --card:#FFFCF4; --ink:#18251F; --gold:#B57A22; --teal:#0D766E; --coral:#B94836; --sky:#2676A8; --border:#D8CBB8; --mono:'IBM Plex Mono',monospace; --sans:Inter,system-ui,sans-serif; }
  * { box-sizing:border-box; } body { font-family:var(--sans); background:var(--bg); color:var(--ink); margin:0; padding:24px; line-height:1.5; }
  h1 { font-family:Georgia,serif; font-size:24px; margin:0 0 4px; } .sub { color:#5D6B62; font-size:13px; margin-bottom:20px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:14px; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:4px; padding:14px; }
  .id { font:600 10px var(--mono); color:#5D6B62; word-break:break-all; margin-bottom:6px; }
  .blocker { font-family:Georgia,serif; font-size:16px; font-weight:700; margin-bottom:8px; }
  .meta { font-size:12px; color:#455A50; margin-bottom:10px; }
  .status { display:inline-block; font:700 9px var(--mono); text-transform:uppercase; padding:2px 8px; border-radius:20px; border:1px solid var(--border); color:#5D6B62; margin-bottom:10px; }
  .status.verified { color:var(--teal); border-color:var(--teal); } .status.active { color:var(--gold); border-color:var(--gold); }
  .btns { display:flex; flex-wrap:wrap; gap:6px; }
  button { font:600 11px var(--sans); padding:6px 10px; border:1px solid var(--border); border-radius:3px; background:var(--card); cursor:pointer; }
  button.ok { color:var(--teal); border-color:var(--teal); } button.intro { color:var(--sky); border-color:var(--sky); }
  button.block { color:var(--coral); border-color:var(--coral); } button.ev { color:var(--ink); }
  button:hover { filter:brightness(0.97); }
  .outcomes { margin-top:8px; font:600 9px var(--mono); color:var(--teal); }
  #toast { position:fixed; bottom:18px; left:50%; transform:translateX(-50%); background:var(--ink); color:var(--bg); padding:10px 16px; border-radius:4px; font-size:13px; opacity:0; transition:opacity .2s; max-width:90vw; }
  #toast.show { opacity:1; }
  .hint { margin-top:24px; background:var(--card); border:1px solid var(--border); border-radius:4px; padding:14px; font:12px var(--mono); color:#455A50; white-space:pre-wrap; }
</style>
</head>
<body>
<h1>Coordination Console</h1>
<div class="sub">Record operator outcomes against interventions. Changes persist locally, then commit + deploy to ship.</div>
<div class="grid" id="grid"></div>
<div class="hint" id="hint"></div>
<div id="toast"></div>
<script>
const STATUS_CLASS = { verified:'verified', proposed:'active', evidence_requested:'active', evidence_received:'active' };
async function load() {
  const r = await fetch('/api'); const data = await r.json();
  const grid = document.getElementById('grid');
  grid.innerHTML = '';
  for (const e of data.interventions) {
    const outcomes = (e.outcomes||[]).map(o=>o.type).join(', ');
    const sc = STATUS_CLASS[e.status] || 'active';
    const card = document.createElement('div'); card.className='card';
    card.innerHTML = `<div class="id">${e.id}</div>
      <div class="blocker">${e.blocker||'—'}</div>
      <div class="meta">owner: ${e.owner_persona||'—'} · related: ${(e.related_signals||[]).join(', ')}</div>
      <div class="status ${sc}">${e.status}</div>
      <div class="btns">
        <button class="ok" onclick="act('${e.id}','supplier_validated')">✓ supplier validated</button>
        <button class="intro" onclick="act('${e.id}','intro_accepted')">↗ intro accepted</button>
        <button class="block" onclick="act('${e.id}','blocked_logistics')">⛔ blocked by logistics</button>
      </div>
      ${outcomes?`<div class="outcomes">outcomes: ${outcomes}</div>`:''}`;
    grid.appendChild(card);
  }
}
async function act(id, type) {
  const note = prompt('Note (optional):', '') || '';
  const r = await fetch('/api', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ action:'submit-outcome', id, type, note }) });
  const j = await r.json();
  toast(j.ok ? `recorded ${type} on ${id}` : `error: ${j.error||'failed'}`);
  if (j.commit_hint) document.getElementById('hint').textContent = j.commit_hint;
  load();
}
function toast(msg){ const t=document.getElementById('toast'); t.textContent=msg; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),2600); }
load();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlparse(self.path).path.rstrip("/") in ("", "/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(HTML)))
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
            return
        if urlparse(self.path).path.rstrip("/") == "/api":
            interventions, _ = _load_mods()
            state = interventions.get_state(ROOT)
            entries = sorted(
                state["interventions"].values(),
                key=lambda e: (e.get("status") != "proposed", e.get("updated_at") or ""),
            )
            self._send({"interventions": entries})
            return
        self._send({"error": "not found"}, 404)

    def do_POST(self):
        if urlparse(self.path).path.rstrip("/") != "/api":
            self._send({"error": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send({"ok": False, "error": "bad json"}, 400)
            return
        interventions, engine = _load_mods()
        action = payload.get("action")
        try:
            if action == "submit-outcome":
                interventions.submit_outcome(
                    payload["id"], payload["type"], payload.get("note", ""), root=ROOT
                )
            elif action == "submit-evidence":
                interventions.add_evidence(
                    payload["id"], payload["summary"], payload["source"],
                    payload.get("country"), root=ROOT
                )
            elif action == "verify":
                interventions.verify(payload["id"], root=ROOT)
            else:
                self._send({"ok": False, "error": f"unknown action: {action}"}, 400)
                return
        except Exception as exc:  # surface real errors, don't pretend success
            self._send({"ok": False, "error": str(exc)}, 400)
            return
        _regenerate(interventions, engine)
        self._send({"ok": True, "commit_hint": _commit_hint()})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Coordination console → http://localhost:{args.port}")
    print("Recording outcomes locally. Commit + deploy to ship to the live site.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
