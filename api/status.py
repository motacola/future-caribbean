"""Vercel serverless function: GET /api/status"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from http.server import BaseHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Reuse logic from server.py but read-only
from agent.query import load_desk  # noqa: E402

SRC = [
    ("World Bank", "world_bank", "REST API · 5 indicators × 13 countries"),
    ("IDB Open Data", "idb", "CKAN API · Regional project datasets"),
    ("NOAA NWS", "noaa", "NWS API · Active hazard alerts"),
    ("NDBC Buoys", "ndbc", "Marine conditions · 6 buoys"),
    ("CARICOM Statistics", "tier2", "WordPress REST · 126 datasets"),
    ("CDB Procurement", "tier2", "RSS · Project & procurement notices"),
]


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _age_minutes(ts: str | None) -> int | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return int((datetime.now(timezone.utc) - dt).total_seconds() / 60)
    except Exception:
        return None


# Grace of one missed refresh before a source is called stale. The pipeline
# cadence is 4h, so the floor here is a full cycle either way.
_DEFAULT_REFRESH_MINUTES = 1440
_STALENESS_GRACE_FACTOR = 2


def _max_age_minutes(health_entry: dict) -> int:
    """Age at which a source stops counting as current.

    Derived from the refresh interval the publisher recorded for that
    source (packagers/source_health.py), so slow annual indicators and
    four-hourly hazard alerts are not judged against the same number.
    """
    try:
        refresh = int(health_entry.get("refresh_minutes") or _DEFAULT_REFRESH_MINUTES)
    except (TypeError, ValueError):
        refresh = _DEFAULT_REFRESH_MINUTES
    return max(refresh, 1) * _STALENESS_GRACE_FACTOR


def _regional_news_summary() -> dict:
    """Build a regional-news freshness summary for the status response.

    Reads from data/regional_news/latest.json when present (local); falls
    back to public/regional_news.json (Astro build output, also in the
    Vercel build context) when data/* is .vercelignore'd. Returns counts
    + the most recent success timestamp so dashboards can show "X fresh
    articles · Y stale".
    """
    candidates = [
        ROOT / "data" / "regional_news" / "latest.json",
        ROOT / "public" / "regional_news.json",
    ]
    payload: dict | None = None
    for path in candidates:
        if path.exists():
            payload = _read_json(path)
            if payload:
                break
    if not payload:
        return {
            "total": 0,
            "fresh_items": 0,
            "fresh_within_48h": 0,
            "stale": True,
            "last_success_at": None,
            "snapshot_age_hours": None,
        }
    items = payload.get("items") or []
    fetched_at = payload.get("fetched_at")
    age_hours: int | None = None
    if fetched_at:
        try:
            dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
            age_hours = int((datetime.now(timezone.utc) - dt).total_seconds() / 3600)
        except Exception:
            age_hours = None
    fresh = 0
    for it in items:
        age = it.get("age_hours")
        if age is None:
            try:
                dt = datetime.fromisoformat(
                    (it.get("published") or "").replace("Z", "+00:00")
                )
                age = int((datetime.now(timezone.utc) - dt).total_seconds() / 3600)
            except Exception:
                continue
        if age <= 48:
            fresh += 1
    return {
        "total": payload.get("total", len(items)),
        "fresh_items": len(items),
        "fresh_within_48h": fresh,
        "stale": (age_hours or 0) > 24,
        "last_success_at": fetched_at,
        "snapshot_age_hours": age_hours,
    }


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
        try:
            desk = load_desk()
            clusters = desk.get("clusters", []) or []
            dispatch_data = _read_json(ROOT / "outbox" / "opportunity_dispatches.json")
            dispatches = dispatch_data.get("dispatches", []) if dispatch_data else []

            # Source health — prefer direct data file, fall back to the bundled
            # snapshot (api/source-health-data.json is committed + in the Vercel
            # build context; data/* is .vercelignore'd). This is the only way
            # /api/status can show real source freshness on Vercel.
            bundled_source_health = _read_json(ROOT / "api" / "source-health-data.json") or {}
            sources = []
            n_sources_ok = 0
            n_sources_stale = 0
            for label, key, desc in SRC:
                d = _read_json(ROOT / "data" / key / "latest.json")
                if d is not None and d.get("ok") is False:
                    # The watcher recorded that this run collected nothing.
                    # Fall through to the last known-good timestamp so the
                    # age keeps growing instead of resetting on every failure.
                    d = None
                fetched_at = (d or {}).get("fetched_at") if d else None
                fallback = bundled_source_health.get(key) or {}
                if not fetched_at:
                    fetched_at = fallback.get("fetched_at")
                ok = bool(fetched_at)
                if ok:
                    n_sources_ok += 1
                age_min = _age_minutes(fetched_at)
                # Staleness is cadence-relative: compare against the source's
                # own refresh interval, not a universal number of days. A
                # source that answered once and then went silent must not keep
                # reading as healthy just because a timestamp exists.
                max_age = _max_age_minutes(fallback)
                stale = age_min is not None and age_min > max_age
                if stale:
                    n_sources_stale += 1
                sources.append({
                    "label": label,
                    "key": key,
                    "description": desc,
                    "ok": ok,
                    "age_minutes": age_min,
                    "max_age_minutes": max_age,
                    "stale": stale,
                    "carried_forward": bool(fallback.get("carried_forward")),
                })

            # Feedback counts — prefer direct data file, fall back to the
            # bundled snapshot (api/feedback-data.json is committed + in the
            # Vercel build context; data/* is .vercelignore'd). Same pattern
            # as the source-health fallback.
            bundled_feedback = _read_json(ROOT / "api" / "feedback-data.json") or {}
            bundled_history = bundled_feedback.get("history") or []
            bundled_actions = bundled_feedback.get("actions") or {}
            bundled_boosts = bundled_feedback.get("boosts") or {}

            fb = _read_json(ROOT / "data" / "feedback" / "state.json") or {}
            fb_hist = fb.get("history", []) or []
            if not fb_hist and bundled_history:
                fb_hist = bundled_history
            fb_boosts = fb.get("boosts", {}) or bundled_boosts
            fb_actions: dict[str, int] = {}
            for e in fb_hist:
                s = e.get("feedback_status", "unknown")
                fb_actions[s] = fb_actions.get(s, 0) + 1
            if not fb_actions and bundled_actions:
                fb_actions = bundled_actions

            cycle_id = desk.get("cycle_id", "unknown")
            cycle_count_path = ROOT / "data" / ".cycle_count.json"
            cycle_count = None
            if cycle_count_path.exists():
                try:
                    cycle_count = int(cycle_count_path.read_text().strip())
                except Exception:
                    pass

            self._json({
                "ok": True,
                "public_mode": True,
                "host": "vercel",
                "cycle_id": cycle_id,
                "cycle_count": cycle_count,
                "cadence_hours": 4,
                "n_sources_ok": n_sources_ok,
                "n_sources_stale": n_sources_stale,
                "n_sources_fresh": n_sources_ok - n_sources_stale,
                "n_sources_total": len(SRC),
                "sources": sources,
                "n_clusters": len(clusters),
                "n_dispatches": len(dispatches),
                "feedback": {
                    "total_responses": len(fb_hist),
                    "actions": fb_actions,
                    "active_boosts": fb_boosts,
                },
                "regional_news": _regional_news_summary(),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
        except FileNotFoundError as exc:
            self._json({"ok": False, "error": str(exc), "note": "Run the pipeline to generate desk artifacts"}, 503)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)