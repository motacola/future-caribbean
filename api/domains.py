"""Vercel serverless function: GET /api/domains — the config-driven engine registry."""
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


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
        try:
            from domains.registry import load_all, summarise
            domains, errors = load_all(validate=True)
            self._json({"ok": True, "count": len(domains),
                        "domains": [summarise(d) for d in domains], "errors": errors})
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)
