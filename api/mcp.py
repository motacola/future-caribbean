"""Vercel serverless function: the MCP endpoint at /mcp.

This is what makes "add Abeng to my agent" work for someone who has not
cloned anything — the same tools the stdio adapter exposes locally, over
Streamable HTTP, on the deployed instance.

Read-only: the public deployment serves the published artefacts and nothing
that writes, which matches how /api/tools.json marks its write tools.
"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcp_adapter.http import handle_payload  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Mcp-Session-Id, MCP-Protocol-Version")
        self.send_header("Access-Control-Expose-Headers", "Mcp-Session-Id")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        # No server-initiated stream: the server is stateless and has nothing
        # to push. Say so rather than leaving a client waiting on a stream.
        self.send_response(405)
        self.send_header("Allow", "POST, OPTIONS")
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(length) if length else b"{}"

        status, response = handle_payload(raw)
        if response is None:
            self.send_response(202)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        body = json.dumps(response, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)
