#!/usr/bin/env python3
"""Serve Caribbean Opportunity Dispatch — product-first homepage with live API."""

import http.server
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

PORT = int(os.environ.get("PORT", 8080))
APP_DIR = Path(__file__).parent

BLOCKED_PREFIXES = (
    ".git", ".env", ".claude", ".hermes", ".ruff_cache", ".github",
    "data/", "signals/", "watchers/", "mergers/", "distributors/",
    "packagers/", "planning/", "tests/", "agent/", "architecture/",
    "config/", "memory/", "domains/",
    "run_pipeline.sh", "requirements.txt", "server.py", "Dockerfile",
    "Procfile", "fly.toml", "vercel.json", ".gitignore", ".dockerignore",
)

_pipeline_lock = threading.Lock()
_pipeline_running = False
_last_pipeline_lines: list[str] = []


class AppHandler(http.server.SimpleHTTPRequestHandler):
    """Handler: file serving + live API endpoints."""

    # ── Routing ────────────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API routes
        if path == "/api/status":
            self._api_status()
            return
        if path == "/api/pipeline/stream":
            self._api_pipeline_stream()
            return
        if path == "/api/whatsapp/link":
            self._api_whatsapp_link()
            return
        if path == "/api/preview":
            self._api_preview()
            return
        if path == "/api/domains":
            self._api_domains()
            return

        # Block internal paths
        clean = path.lstrip("/")
        for blocked in BLOCKED_PREFIXES:
            if clean == blocked or clean.startswith(blocked):
                self.send_error(404)
                return

        # Root → Signal Builder; /system → audit dashboard
        if clean in ("", "index.html"):
            self.path = "/configurator.html"
        elif clean in ("system", "system.html"):
            self.path = "/dashboard.html"

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/send/telegram":
            self._api_send("telegram")
        elif path == "/api/whatsapp/link":
            self._api_whatsapp_link()
        else:
            self.send_error(404)

    # ── API helpers ────────────────────────────────────────────

    def _json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")

    def _sse(self, data: str) -> bool:
        """Write one SSE message. Returns False if the connection broke."""
        try:
            line = data.replace("\n", " ").replace("\r", "")
            self.wfile.write(f"data: {line}\n\n".encode("utf-8"))
            self.wfile.flush()
            return True
        except Exception:
            return False

    # ── /api/domains ───────────────────────────────────────────

    def _api_domains(self) -> None:
        """Serve the domain registry — the proof that the engine is
        config-driven. Each entry is a real domains/*.json manifest."""
        try:
            sys.path.insert(0, str(APP_DIR))
            from domains.registry import load_all, summarise
            domains, errors = load_all(validate=True)
            self._json({
                "ok": True,
                "count": len(domains),
                "domains": [summarise(d) for d in domains],
                "errors": errors,
            })
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    # ── /api/status ────────────────────────────────────────────

    def _api_status(self) -> None:
        global _pipeline_running

        source_keys = {
            "World Bank": "world_bank",
            "IDB": "idb",
            "NOAA": "noaa",
            "NDBC": "ndbc",
            "CARICOM / CDB": "tier2",
        }
        sources: dict = {}
        for name, key in source_keys.items():
            p = APP_DIR / "data" / key / "latest.json"
            ok = p.exists()
            fetched_at = ""
            if ok:
                try:
                    d = json.loads(p.read_text())
                    fetched_at = d.get("fetched_at", "")
                except Exception:
                    pass
            sources[key] = {"name": name, "ok": ok, "fetched_at": fetched_at}

        desk: dict = {}
        desk_p = APP_DIR / "outbox" / "dispatch_desk.json"
        if desk_p.exists():
            try:
                desk = json.loads(desk_p.read_text())
            except Exception:
                pass

        self._json({
            "ok": True,
            "sources": sources,
            "n_sources_ok": sum(1 for s in sources.values() if s["ok"]),
            "n_dispatches": desk.get("dispatch_count", 0),
            "n_clusters": len(desk.get("clusters", [])),
            "cycle_id": desk.get("cycle_id", "—"),
            "generated_at": desk.get("generated_at", ""),
            "pipeline_running": _pipeline_running,
            "last_lines": _last_pipeline_lines[-8:],
            "server_time": datetime.now(timezone.utc).isoformat(),
        })

    # ── /api/send/telegram ─────────────────────────────────────

    def _api_send(self, channel: str) -> None:
        script = APP_DIR / "distributors" / "telegram_sender.py"
        if not script.exists():
            self._json({"ok": False, "error": "telegram_sender.py not found"}, 404)
            return

        # Load .env if present; use live mode if token present, else dry-run
        env = os.environ.copy()
        env_path = APP_DIR / ".env"
        if env_path.exists():
            for raw in env_path.read_text().splitlines():
                raw = raw.strip()
                if raw and not raw.startswith("#") and "=" in raw:
                    k, _, v = raw.partition("=")
                    env.setdefault(k.strip(), v.strip())

        has_creds = bool(env.get("TELEGRAM_BOT_TOKEN"))
        flags = [] if has_creds else ["--dry-run"]

        try:
            result = subprocess.run(
                ["python3", str(script)] + flags,
                capture_output=True, text=True, timeout=25,
                cwd=str(APP_DIR), env=env,
            )
            output = (result.stdout or "") + (result.stderr or "")
            self._json({
                "ok": result.returncode == 0,
                "channel": "telegram",
                "mode": "live" if has_creds else "dry-run",
                "output": output[:800].strip(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except subprocess.TimeoutExpired:
            self._json({"ok": False, "error": "Timeout after 25s"}, 504)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    # ── /api/preview ───────────────────────────────────────────

    def _api_preview(self) -> None:
        import re
        from urllib.parse import parse_qs

        qs = parse_qs(urlparse(self.path).query)
        persona   = qs.get("persona",  ["investor"])[0].lower().strip()
        countries = [c.strip() for c in qs.get("countries", ["all"])[0].lower().split(",") if c.strip()]
        signals   = [s.strip() for s in qs.get("signals",   ["all"])[0].lower().split(",") if s.strip()]
        channel   = qs.get("channel",  ["telegram"])[0].lower().strip()

        # Load live dispatch data
        desk: dict = {}
        desk_p = APP_DIR / "outbox" / "dispatch_desk.json"
        if desk_p.exists():
            try:
                desk = json.loads(desk_p.read_text())
            except Exception:
                pass

        clusters = desk.get("clusters", [])
        if not clusters:
            self._json({"ok": False, "error": "No signal data yet — run the pipeline first."}, 503)
            return

        # ── Country filter ─────────────────────────────────────
        fallback = False
        fallback_reason = ""
        working = clusters

        if "all" not in countries:
            matched = [
                c for c in clusters
                if any(co in c.get("country_cluster", "").lower() for co in countries)
            ]
            if matched:
                working = matched
            else:
                fallback = True
                fallback_reason = "No signals for selected countries this cycle. Showing nearest available signal."

        # ── Signal-type filter ──────────────────────────────────
        SIG_TERMS: dict[str, list[str]] = {
            "investment":  ["investment", "capital", "fdi", "surge", "momentum"],
            "procurement": ["procurement", "cdb", "idb", "pipeline", "project"],
            "risk":        ["risk", "vulnerability", "debt", "deficit"],
            "weather":     ["weather", "marine", "storm", "hurricane", "pressure", "wind", "wave"],
            "tourism":     ["tourism", "logistics", "travel", "hospitality"],
        }
        if "all" not in signals:
            terms: list[str] = []
            for s in signals:
                terms.extend(SIG_TERMS.get(s, [s]))
            sig_matched = [
                c for c in working
                if any(t in (c.get("title","") + c.get("evidence","")).lower() for t in terms)
            ]
            if sig_matched:
                working = sig_matched
            elif not fallback:
                fallback = True
                fallback_reason = "No exact match for selected signal types this cycle. Showing nearest relevant signal."

        cluster = working[0]

        # ── Persona matching ────────────────────────────────────
        PERSONA_TERMS: dict[str, list[str]] = {
            "investor":  ["investor", "diaspora investor", "regional investor"],
            "founder":   ["founder", "operator", "ecosystem builder"],
            "policy":    ["policy", "media", "policy/media"],
            "diaspora":  ["diaspora"],
        }
        p_terms = PERSONA_TERMS.get(persona, [persona])
        persona_rec: dict = {}
        for p in cluster.get("personas", []):
            if any(t in p.get("persona", "").lower() for t in p_terms):
                persona_rec = p
                break
        if not persona_rec and cluster.get("personas"):
            persona_rec = cluster["personas"][0]

        # ── Field extraction ────────────────────────────────────
        country  = cluster.get("country_cluster", "Caribbean")
        raw_title = cluster.get("title", "")
        evidence = cluster.get("evidence", "")
        grade    = (cluster.get("evidence_grade", "C") or "C")[0].upper()
        decision = cluster.get("decision", "")
        risks    = cluster.get("risk_flags", []) or []

        # Clean evidence text — strip redundant country (shown separately),
        # then humanise pipeline shorthand
        evidence = re.sub(rf"^\s*{re.escape(country)}\s*:\s*", "", evidence)
        evidence = re.sub(rf"\s*:\s*{re.escape(country)}\s*\.?\s*$", "", evidence)
        evidence = re.sub(r"\bWB\b", "World Bank", evidence)
        evidence = re.sub(r"FDI surge detected", "FDI inflows rising", evidence)
        evidence = re.sub(r"detected:\s*", "", evidence)
        evidence = re.sub(r"FDI surge", "FDI movement", evidence)
        evidence = evidence.strip()

        pct_m = re.search(r"([+\-]?\d+\.?\d*)%", raw_title)
        pct   = pct_m.group(0) if pct_m else ""

        conf_map = {"A": "High confidence", "B": "Moderate confidence", "C": "Early signal"}
        confidence = conf_map.get(grade, "Early signal")

        action = persona_rec.get("action", decision)[:200] if persona_rec else decision[:200]

        PERSONA_DISPLAY = {
            "investor": "Diaspora Investor",
            "founder":  "Regional Founder / Operator",
            "policy":   "Policy / Media",
            "diaspora": "Diaspora",
        }
        persona_label = PERSONA_DISPLAY.get(persona, persona.title())

        # ── Format per channel ──────────────────────────────────
        pct_str = f" ({pct})" if pct else ""

        if channel == "telegram":
            formatted = (
                f"*Caribbean Opportunity Signal*\n\n"
                f"*{country}* — {confidence}\n\n"
                f"{evidence}{pct_str}\n\n"
                f"*What to do ({persona_label}):*\n{action}\n\n"
                + (f"⚠️ Risk flag: {risks[0]}\n\n" if risks else "")
                + "_Screening signal only. Not investment advice._"
            )
        elif channel == "whatsapp":
            formatted = (
                f"🌴 Caribbean Signal\n\n"
                f"{country}: {evidence}{pct_str}\n\n"
                f"{action[:160]}\n\n"
                f"Screening signal only. Not investment advice.\n"
                f"Full brief: https://future-caribbean.fly.dev"
            )
        elif channel == "email":
            formatted = (
                f"Subject: {country} — {confidence.lower()} market signal\n\n"
                f"{evidence}{pct_str}\n\n"
                f"For {persona_label}:\n{action}\n\n"
                + (f"Risk flag: {risks[0]}\n\n" if risks else "")
                + f"Source: World Bank indicators\nConfidence: {confidence}\n\n"
                f"Screening signal, not investment advice.\n"
                f"Caribbean Opportunity Dispatch"
            )
        else:  # memo
            formatted = (
                f"CARIBBEAN OPPORTUNITY BRIEF\n"
                f"{'─' * 36}\n"
                f"Country:    {country}\n"
                f"Confidence: {confidence}\n"
                f"Audience:   {persona_label}\n\n"
                f"SIGNAL\n{evidence}{pct_str}\n\n"
                f"RECOMMENDED ACTION\n{action}\n\n"
                + (f"RISK FLAG\n{risks[0]}\n\n" if risks else "")
                + f"{'─' * 36}\n"
                f"Screening signal only. Not investment advice.\n"
                f"Caribbean Opportunity Dispatch"
            )

        self._json({
            "ok":             True,
            "persona":        persona_label,
            "channel":        channel,
            "country":        country,
            "confidence":     confidence,
            "evidence":       evidence,
            "pct":            pct,
            "action":         action,
            "source":         "World Bank / IDB / NOAA / CARICOM / CDB",
            "risks":          risks[:1],
            "formatted":      formatted,
            "fallback":       fallback,
            "fallback_reason": fallback_reason,
            "cycle_id":       desk.get("cycle_id", ""),
        })

    # ── /api/whatsapp/link ─────────────────────────────────────

    def _api_whatsapp_link(self) -> None:
        """Return a pre-filled wa.me share link built from the live dispatch."""
        import urllib.parse

        desk: dict = {}
        desk_p = APP_DIR / "outbox" / "dispatch_desk.json"
        if desk_p.exists():
            try:
                desk = json.loads(desk_p.read_text())
            except Exception:
                pass

        clusters = desk.get("clusters", [])
        lead = clusters[0] if clusters else {}
        country = lead.get("country_cluster", "Caribbean")
        title = lead.get("title", "")

        # Extract percentage if present
        import re
        pct_m = re.search(r"([+\-]?\d+\.?\d*)%", title)
        pct = pct_m.group(0) if pct_m else ""

        lines = [
            "🌴 *Caribbean Opportunity Signal*",
            "",
            f"*Lead market: {country}*",
            f"Signal: {pct} capital movement (World Bank data)" if pct else "Signal: Capital momentum detected",
            "",
            "Who should act: Diaspora investors, regional founders, ecosystem builders.",
            "",
            f"Next step: Screen {country} first. Validate sector fit and local partners before committing.",
            "",
            "_Screening signal only. Not investment advice._",
            "",
            "Full brief: https://future-caribbean.fly.dev",
        ]
        msg = "\n".join(lines)

        # wa.me uses plain text (no markdown)
        plain = msg.replace("*", "").replace("_", "")
        link = "https://wa.me/?text=" + urllib.parse.quote(plain)

        self._json({
            "ok": True,
            "link": link,
            "preview": plain[:300],
            "country": country,
        })

    # ── /api/pipeline/stream (SSE) ─────────────────────────────

    def _api_pipeline_stream(self) -> None:
        global _pipeline_running, _last_pipeline_lines

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self._cors()
        self.end_headers()

        if not _pipeline_lock.acquire(blocking=False):
            self._sse("⏳ Pipeline already running — please wait…")
            return

        _pipeline_running = True
        _last_pipeline_lines = []
        try:
            self._sse("🚀 Starting Caribbean Signal OS pipeline…")
            proc = subprocess.Popen(
                ["bash", "run_pipeline.sh"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, cwd=str(APP_DIR),
            )
            for raw in proc.stdout:  # type: ignore[union-attr]
                line = raw.rstrip()
                if not line:
                    continue
                _last_pipeline_lines.append(line)
                if len(_last_pipeline_lines) > 80:
                    _last_pipeline_lines = _last_pipeline_lines[-80:]
                if not self._sse(line):
                    proc.terminate()
                    break
            proc.wait()
            self._sse(f"✅ Pipeline complete — exit {proc.returncode}")
        except Exception as exc:
            self._sse(f"❌ Error: {exc}")
        finally:
            _pipeline_running = False
            _pipeline_lock.release()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def log_message(self, format, *args):
        pass


def pipeline_loop():
    """Run the pipeline on startup and every 4 hours."""
    time.sleep(3)
    subprocess.run(["bash", "run_pipeline.sh"], capture_output=True, cwd=str(APP_DIR))
    while True:
        time.sleep(14400)
        subprocess.run(["bash", "run_pipeline.sh"], capture_output=True, cwd=str(APP_DIR))


if __name__ == "__main__":
    threading.Thread(target=pipeline_loop, daemon=True).start()
    os.chdir(str(APP_DIR))
    server = http.server.HTTPServer(("0.0.0.0", PORT), AppHandler)
    print(f"Listening on :{PORT}")
    server.serve_forever()
