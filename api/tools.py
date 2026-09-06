"""Vercel serverless function: GET /api/tools.json — public variant with write tools marked unavailable"""
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api_manifest import manifest_for  # noqa: E402


# The deployment's own address, so an agent that ingests the manifest can
# call the tools without being told where they live. Vercel passes the real
# host through; the fallback is the documented public instance.
PUBLIC_BASE_URL = "https://abeng.vercel.app"


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
        host = self.headers.get("Host")
        base = f"https://{host}" if host else PUBLIC_BASE_URL
        self._json(manifest_for(base, public=True))