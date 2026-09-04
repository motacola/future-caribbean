"""Vercel serverless function: read-only artifact endpoints served by one function.

Vercel's Hobby plan allows 12 Serverless Functions per deployment. api/ had 15,
so three were silently dropped from every deploy — /api/regional-news (which the
public tool manifest advertises), /api/market-watch and /api/ping all returned
404 in production while working fine locally.

The endpoints below were four separate files that did the same thing: read one
generated artifact and return it. Collapsing them into one dispatcher puts the
deployment back under the cap with a slot to spare, and keeps every public path
and response shape exactly as it was — vercel.json rewrites each path to this
function with a `doc` parameter.

Response shapes are load-bearing: `reasoning`, `track-record` and `calibration`
return {"ok": true, ...artifact} and 503 with a run-the-pipeline message when the
artifact is absent, while `map-data` returns the computed payload unwrapped.
Changing any of those would break the site, the CLI, the MCP adapter, or an agent
following /api/tools.json.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# doc -> (artifact path relative to ROOT, message when it has not been generated)
PASSTHROUGH = {
    "reasoning": ("outbox/reasoning.json", "No synthesis yet — run the pipeline."),
    "track-record": ("outbox/track_record.json", "Track record not generated yet — run the pipeline."),
    "calibration": ("outbox/calibration.json", "Calibration report not generated yet — run the pipeline."),
}


def resolve(doc: str, root: Path = ROOT):
    """Return (status, payload) for a doc name. Pure, so it can be tested directly."""
    if doc == "map-data":
        try:
            from map_data import build_map_data
            return 200, build_map_data(root)
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller as JSON
            return 500, {"error": str(exc)}

    entry = PASSTHROUGH.get(doc)
    if entry is None:
        return 404, {"ok": False, "error": f"unknown artifact: {doc}"}

    relative, missing_message = entry
    path = root / relative
    if not path.exists():
        return 503, {"ok": False, "error": missing_message}
    try:
        return 200, {"ok": True, **json.loads(path.read_text(encoding="utf-8"))}
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller as JSON
        return 500, {"ok": False, "error": str(exc)}


class handler(BaseHTTPRequestHandler):
    def _json(self, data, status: int = 200) -> None:
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
        doc = parse_qs(urlparse(self.path).query).get("doc", [""])[0]
        status, payload = resolve(doc)
        self._json(payload, status)
