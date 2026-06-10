"""Vercel serverless function: GET /api/validation-packs/[id]"""
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler

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
        # Vercel provides the path param via the request path
        # The path will be like /api/validation-packs/enhanced-invest-guyana
        path = self.path
        prefix = "/api/validation-packs/"
        if not path.startswith(prefix):
            self._json({"error": "Invalid path"}, 400)
            return

        signal_id = path[len(prefix):]
        # Sanitize - reject traversal attempts
        if "/" in signal_id or ".." in signal_id:
            self._json({"error": "Invalid signal_id"}, 400)
            return

        # Vercel serves files with .json extension in the static file system
        # The committed files are named like enhanced-invest-guyana.json
        # But the index.json references them with the file field
        pack_path = ROOT / "outbox" / "validation_packs" / f"{signal_id}.json"
        if not pack_path.exists():
            self._json({"error": f"Validation pack '{signal_id}' not found"}, 404)
            return
        try:
            pack = json.loads(pack_path.read_text(encoding="utf-8"))
            self._json(pack)
        except Exception as exc:
            self._json({"error": str(exc)}, 500)