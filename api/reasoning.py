"""Vercel serverless function: GET /api/reasoning — cross-signal synthesis."""
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1]


class handler(BaseHTTPRequestHandler):
    def _json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = ROOT / "outbox" / "reasoning.json"
        if not p.exists():
            self._json({"ok": False, "error": "No synthesis yet — run the pipeline."}, 503)
            return
        try:
            self._json({"ok": True, **json.loads(p.read_text())})
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)
