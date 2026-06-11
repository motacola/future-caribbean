"""Vercel serverless function: GET /api/validation-packs[?id=<signal_id>]

Without ?id: the pack index. With ?id: the full pack for that signal
(pretty path /api/validation-packs/<id> rewrites to ?id= via vercel.json).
"""
import json
import re
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


class handler(BaseHTTPRequestHandler):
    def _json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        packs_dir = ROOT / "outbox" / "validation_packs"
        qs = parse_qs(urlparse(self.path).query)
        sid = (qs.get("id") or [""])[0]
        if sid:
            safe = re.sub(r"[^A-Za-z0-9._-]", "-", sid)
            pack = _read_json(packs_dir / f"{safe}.json")
            if pack is None:
                self._json({"error": f"No validation pack for signal '{sid}'."}, 404)
            else:
                self._json(pack)
            return
        index = _read_json(packs_dir / "index.json")
        if index is None:
            self._json({"error": "No validation packs index found — run the pipeline first."}, 404)
        else:
            self._json(index)