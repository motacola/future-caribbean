"""Consolidated Vercel procurement read function.

``/api/procurement-outcomes`` is the read-only canonical outcome view: what was detected,
when, what changed, and what happened to it. Serves exactly the artefact
the Opportunity Resolution page renders, so the API and the page cannot
disagree about a record.

``/api/capability-matches`` is rewritten here with
``?view=capability_matches`` to stay within Vercel's 12-function Hobby-plan
limit. It serves the cited country/bloc screening matches artifact.

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
CAPABILITY_MATCHES = ROOT / "outbox" / "capability_matches.json"

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


def filter_capability_matches(matches: list[dict], params: dict) -> list[dict]:
    country = (params.get("country", [""])[0] or "").strip().lower()
    capability = (params.get("capability", [""])[0] or "").strip().lower()
    out = matches
    if country:
        out = [m for m in out if (m.get("country") or "").lower() == country]
    if capability:
        out = [
            m for m in out
            if any(
                (c.get("capability") or "").lower() == capability
                for c in (m.get("capability_matches") or [])
            )
        ]
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
        params = parse_qs(urlparse(self.path).query)
        if params.get("view") == ["capability_matches"]:
            try:
                payload = json.loads(CAPABILITY_MATCHES.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                self._json({"ok": False, "error": "capability matches not published yet"}, status=503)
                return
            matches = filter_capability_matches(payload.get("matches", []), params)
            limit = _int_param(params, "limit", DEFAULT_LIMIT, MAX_LIMIT)
            self._json({
                "ok": True,
                "schema_version": payload.get("schema_version"),
                "registry_status": payload.get("registry_status"),
                "total_tenders": payload.get("total_tenders"),
                "classified_tenders": payload.get("classified_tenders"),
                "tenders_with_capability_match": payload.get("tenders_with_capability_match"),
                "by_capability": payload.get("by_capability", {}),
                "by_country": payload.get("by_country", {}),
                "count_semantics": payload.get("count_semantics", {}),
                "count": len(matches),
                "returned": min(len(matches), limit),
                "matches": matches[:limit],
            })
            return

        payload = _load()
        if not payload:
            self._json({
                "ok": False,
                "error": "procurement outcomes not published yet",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }, status=503)
            return

        tenders = filter_tenders(payload.get("tenders", []), params)
        limit = _int_param(params, "limit", DEFAULT_LIMIT, MAX_LIMIT)

        self._json({
            "ok": True,
            "schema_version": payload.get("schema_version"),
            "generated_at": payload.get("generated_at"),
            "corpus_updated_at": payload.get("corpus_updated_at"),
            "summary": payload.get("summary", {}),
            "provenance": payload.get("provenance", {}),
            "coverage": payload.get("coverage", {}),
            "count": len(tenders),
            "returned": min(len(tenders), limit),
            "tenders": tenders[:limit],
        })
