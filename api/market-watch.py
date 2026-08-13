"""Vercel serverless function: freshness-aware Caribbean Market Watch snapshot."""
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]


def _age_days(value, now=None):
    if not value:
        return None
    now = now or datetime.now(timezone.utc)
    try:
        observed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        try:
            observed = datetime.strptime(str(value), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return max(0, (now.date() - observed.astimezone(timezone.utc).date()).days)


def _refresh_market(row, now=None):
    now = now or datetime.now(timezone.utc)
    if row.get("freshness_state") == "proxy_watch":
        return row
    age_days = _age_days(row.get("observation_at"), now)
    if age_days is None:
        state = "source_checked_no_dated_observation" if row.get("fetch_status") == "ok" else row.get("freshness_state", "unavailable")
    else:
        state = "current" if age_days <= 3 else "delayed" if age_days <= 10 else "stale"
    if row.get("fetch_status") == "fallback_cached":
        state = "stale_fallback"
    return {**row, "observation_age_days": age_days, "freshness_state": state}


def payload_health(payload, markets, now=None):
    now = now or datetime.now(timezone.utc)
    fetched = payload.get("fetched_at")
    snapshot_age_hours = None
    if fetched:
        try:
            stamp = datetime.fromisoformat(str(fetched).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            snapshot_age_hours = max(0, int((now - stamp.astimezone(timezone.utc)).total_seconds() // 3600))
        except ValueError:
            pass
    base = dict(payload.get("health") or {})
    base.update({
        "snapshot_age_hours": snapshot_age_hours,
        "stale": snapshot_age_hours is None or snapshot_age_hours > 8,
        "current_observations": sum(row.get("freshness_state") == "current" for row in markets),
        "dated_observations": sum(bool(row.get("observation_at")) for row in markets),
    })
    return base


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        sources = (
            Path(__file__).with_name("market-watch-data.json"),
            ROOT / "public" / "market_watch.json",
            ROOT / "data" / "market_watch" / "latest.json",
        )
        source = next((candidate for candidate in sources if candidate.exists()), None)
        try:
            payload = json.loads(source.read_text(encoding="utf-8")) if source else {"markets": []}
            markets = [_refresh_market(row) for row in payload.get("markets", [])]
            market_id = query.get("id", [None])[0]
            country = query.get("country", [None])[0]
            if market_id:
                markets = [row for row in markets if row.get("id") == market_id]
            if country:
                markets = [row for row in markets if row.get("country") == country]
            body = json.dumps({
                "ok": True,
                "fetched_at": payload.get("fetched_at"),
                "method": payload.get("method"),
                "count": len(markets),
                "health": payload_health(payload, markets),
                "markets": markets,
            }, ensure_ascii=False).encode()
            self.send_response(200)
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}).encode()
            self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
