#!/usr/bin/env python3
"""Serve Caribbean Opportunity Dispatch — product-first homepage with live API."""

import http.server
import json
import mimetypes
import os
import subprocess
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
    "config/", "memory/",
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

        # Block internal paths
        clean = path.lstrip("/")
        for blocked in BLOCKED_PREFIXES:
            if clean == blocked or clean.startswith(blocked):
                self.send_error(404)
                return

        # Root → dashboard
        if clean in ("", "index.html"):
            self.path = "/dashboard.html"

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/send/telegram":
            self._api_send("telegram")
        elif path == "/api/send/whatsapp":
            self._api_send("whatsapp")
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

    # ── /api/send/{channel} ────────────────────────────────────

    def _api_send(self, channel: str) -> None:
        script_map = {
            "telegram": APP_DIR / "distributors" / "telegram_sender.py",
            "whatsapp": APP_DIR / "distributors" / "whatsapp_sender.py",
        }
        script = script_map.get(channel)
        if not script or not script.exists():
            self._json({"ok": False, "error": f"{channel} sender not found"}, 404)
            return

        # Check for credentials; run live if present, dry-run otherwise
        env = os.environ.copy()
        env_path = APP_DIR / ".env"
        if env_path.exists():
            for raw in env_path.read_text().splitlines():
                raw = raw.strip()
                if raw and not raw.startswith("#") and "=" in raw:
                    k, _, v = raw.partition("=")
                    env.setdefault(k.strip(), v.strip())

        has_creds = (
            (channel == "telegram" and env.get("TELEGRAM_BOT_TOKEN"))
            or (channel == "whatsapp" and env.get("TWILIO_ACCOUNT_SID"))
        )
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
                "channel": channel,
                "mode": "live" if has_creds else "dry-run",
                "output": output[:800].strip(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except subprocess.TimeoutExpired:
            self._json({"ok": False, "error": "Timeout after 25s"}, 504)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

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
