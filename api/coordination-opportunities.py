"""Vercel function serving deterministic coordination opportunities."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "outbox" / "coordination_opportunities.json"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            self._send({"error": f"Coordination opportunities unavailable: {exc}"}, 404)
            return
        path = urlparse(self.path).path.rstrip("/")
        prefix = "/api/coordination-opportunities"
        opportunity_id = path[len(prefix):].strip("/") if path.startswith(prefix) else ""
        if opportunity_id:
            item = next((entry for entry in data.get("opportunities", []) if entry.get("id") == opportunity_id), None)
            if item is None:
                self._send({"error": "Coordination opportunity not found"}, 404)
                return
            self._send(item)
            return
        self._send(data)

    def _send(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
