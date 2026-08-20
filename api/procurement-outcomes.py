"""Vercel serverless function: GET /api/procurement-outcomes

Read-only view of the canonical procurement corpus: what was detected,
when, what changed, and what happened to it. Serves exactly the artefact
the Opportunity Resolution page renders, so the API and the page cannot
disagree about a record.

Query params:
  country=<name>     filter to one jurisdiction
  state=<lifecycle>  detected|open|amended|closed|awarded|cancelled|unresolved
  resolved=true      only tenders with a recorded outcome
  limit=<n>          cap the record list (default 100, max 500)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]

# outbox/ is the published artefact; public/ is the copy Astro bakes in.
CANDIDATES = (
    ROOT / "outbox" / "procurement_outcomes.json",
    ROOT / "public" / "procurement_outcomes.json",
)

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def _load() -> dict | None:
    for path in CANDIDATES:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
    return None


def _int_param(params: dict, name: str, default: int, cap: int) -> int:
    try:
        return max(1, min(cap, int(params.get(name, [default])[0])))
    except (TypeError, ValueError):
        return default


def filter_tenders(tenders: list[dict], params: dict) -> list[dict]:
    country = (params.get("country", [""])[0] or "").strip().lower()
    state = (params.get("state", [""])[0] or "").strip().lower()
    resolved_only = (params.get("resolved", [""])[0] or "").strip().lower() in {"1", "true", "yes"}

    out = tenders
    if country:
        out = [t for t in out if (t.get("country") or "").lower() == country]
    if state:
        out = [t for t in out if (t.get("lifecycle_state") or "").lower() == state]
    if resolved_only:
        out = [t for t in out if t.get("resolution")]
    return out


class handler(BaseHTTPRequestHandler):
    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=300")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        payload = _load()
        if not payload:
            self._json({
                "ok": False,
                "error": "procurement outcomes not published yet",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }, status=503)
            return

        params = parse_qs(urlparse(self.path).query)
        tenders = filter_tenders(payload.get("tenders", []), params)
        limit = _int_param(params, "limit", DEFAULT_LIMIT, MAX_LIMIT)

        self._json({
            "ok": True,
            "schema_version": payload.get("schema_version"),
            "generated_at": payload.get("generated_at"),
            "corpus_updated_at": payload.get("corpus_updated_at"),
            "summary": payload.get("summary", {}),
            "provenance": payload.get("provenance", {}),
            "count": len(tenders),
            "returned": min(len(tenders), limit),
            "tenders": tenders[:limit],
        })
