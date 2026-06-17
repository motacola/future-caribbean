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

            # Source health
            sources = []
            n_sources_ok = 0
            for label, key, desc in SRC:
                d = _read_json(ROOT / "data" / key / "latest.json")
                ok = d is not None
                if ok:
                    n_sources_ok += 1
                age_min = _age_minutes(d.get("fetched_at") if d else None)
                sources.append({
                    "label": label,
                    "key": key,
                    "description": desc,
                    "ok": ok,
                    "age_minutes": age_min,
                })

            # Feedback counts
            fb = _read_json(ROOT / "data" / "feedback" / "state.json") or {}
            fb_hist = fb.get("history", []) or []
            fb_boosts = fb.get("boosts", {})
            fb_actions: dict[str, int] = {}
            for e in fb_hist:
                s = e.get("feedback_status", "unknown")
                fb_actions[s] = fb_actions.get(s, 0) + 1

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
                "n_sources_total": len(SRC),
                "sources": sources,
                "n_clusters": len(clusters),
                "n_dispatches": len(dispatches),
                "feedback": {
                    "total_responses": len(fb_hist),
                    "actions": fb_actions,
                    "active_boosts": fb_boosts,
                },
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
        except FileNotFoundError as exc:
            self._json({"ok": False, "error": str(exc), "note": "Run the pipeline to generate desk artifacts"}, 503)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)