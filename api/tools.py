"""Vercel serverless function: GET /api/tools.json — public variant with write tools marked unavailable"""
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api_manifest import TOOLS_MANIFEST  # noqa: E402


def _public_manifest() -> dict:
    """Return a copy of TOOLS_MANIFEST with write tools marked as unavailable on public deploy."""
    import copy
    manifest = copy.deepcopy(TOOLS_MANIFEST)
    for tool in manifest["tools"]:
        if tool.get("writes"):
            tool["available"] = False
            tool["note"] = "local instance only"
        else:
            tool["available"] = True
    return manifest


PUBLIC_MANIFEST = _public_manifest()


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
        self._json(PUBLIC_MANIFEST)