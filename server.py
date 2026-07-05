#!/usr/bin/env python3
"""Serve Caribbean Opportunity Dispatch — product-first homepage with live API."""

import http.server
import json
import os
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get("PORT", 8080))
APP_DIR = Path(__file__).parent

BLOCKED_PREFIXES = (
    ".git", ".env", ".claude", ".hermes", ".ruff_cache", ".github",
    "data/", "signals/", "watchers/", "mergers/", "distributors/",
    "packagers/", "planning/", "tests/", "agent/", "architecture/",
    "config/", "memory/", "domains/", "cli/", "reasoners/",
    "run_pipeline.sh", "requirements.txt", "server.py", "Dockerfile",
    "Procfile", "fly.toml", "vercel.json", ".gitignore", ".dockerignore",
)

_pipeline_lock = threading.Lock()
_pipeline_running = False
_last_pipeline_lines: list[str] = []
_pipeline_subscribers: set[queue.Queue] = set()
_pipeline_subscribers_lock = threading.Lock()


# ── Tool Manifest ────────────────────────────────────────────

from api_manifest import TOOLS_MANIFEST


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
        if path == "/build":
            self.path = "/dist/build/index.html"
            super().do_GET()
            return
        if path == "/feed.xml":
            fp = APP_DIR / "outbox" / "feed.xml"
            if fp.exists():
                body = fp.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/rss+xml; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self._cors()
                self.end_headers()
                self.wfile.write(body)
            else:
                self._json({"error": "feed not generated yet"}, 404)
            return
        if path == "/api/status":
            self._api_status()
            return
        if path == "/api/map-data":
            self._api_map_data()
            return
        if path == "/api/pipeline/stream":
            self._api_pipeline_stream(parse_qs(parsed.query).get("replay") == ["1"])
            return
        if path == "/api/pipeline/status":
            self._api_status()
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
        if path == "/api/reasoning":
            self._api_reasoning()
            return
        if path == "/api/track-record":
            self._api_track_record()
            return
        if path == "/api/delivery/approvals":
            self._api_delivery_approvals()
            return
        if path == "/api/history":
            self._api_history()
            return
        if path == "/api/validation-packs":
            self._api_validation_packs_index()
            return
        if path.startswith("/api/validation-packs/"):
            signal_id = path[len("/api/validation-packs/"):]
            self._api_validation_pack(signal_id)
            return
        if path == "/api/community-brief":
            self._api_community_brief()
            return
        if path == "/api/community-brief/snippets":
            self._api_community_brief_snippets()
            return
        if path == "/api/tools.json":
            self._api_tools_manifest()
            return
        if path == "/api/webhooks":
            self._api_webhooks_list()
            return
        if path == "/llms.txt":
            self._serve_static("llms.txt")
            return
        if path == "/agents.md":
            self._serve_static("agents.md")
            return

        # Block internal paths
        clean = path.lstrip("/")
        for blocked in BLOCKED_PREFIXES:
            if clean == blocked or clean.startswith(blocked):
                self.send_error(404)
                return

        # Astro dist assets
        if clean.startswith("_astro/"):
            self.path = "/dist/" + clean
        # Signal permalink pages
        elif clean.startswith("signal/"):
            self.path = "/dist/" + clean + "/index.html"
        # Root and named pages — serve from Astro dist
        elif clean in ("", "index.html", "briefing", "briefing.html", "desk", "system", "system.html"):
            self.path = "/dist/index.html"
        elif clean in ("build", "build.html"):
            self.path = "/dist/build/index.html"
        # Legacy pages retired June 2026 — redirect old links to Astro routes
        elif clean == "dashboard.html":
            self.send_response(301)
            self.send_header("Location", "/")
            self.end_headers()
            return
        elif clean == "configurator.html":
            self.send_response(301)
            self.send_header("Location", "/build")
            self.end_headers()
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/ask":
            self._api_ask()
            return
        if path == "/api/send/telegram":
            self._api_send("telegram")
        elif path == "/api/whatsapp/link":
            self._api_whatsapp_link()
        elif path == "/api/domains/create":
            self._api_create_domain()
        elif path == "/api/feedback/apply":
            self._api_feedback_apply()
        elif path == "/api/delivery/prepare":
            self._api_delivery_prepare()
        elif path == "/api/delivery/approve":
            self._api_delivery_approve()
        elif path == "/api/delivery/send-approved":
            self._api_delivery_send_approved()
        elif path == "/api/history/archive":
            self._api_history_archive()
        elif path == "/api/webhooks/subscribe":
            self._api_webhooks_subscribe()
        else:
            self.send_error(404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/webhooks/"):
            sub_id = path[len("/api/webhooks/"):]
            self._api_webhooks_delete(sub_id)
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

    def _read_json_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
            return body if isinstance(body, dict) else {}
        except Exception:
            return {}

    def _run_node_workflow(self, workflow: str, payload: dict, timeout: int = 90) -> dict:
        cmd = ["npm", "exec", "--", "flue", "run", workflow, "--target", "node", "--payload", json.dumps(payload)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(APP_DIR))
        output = (result.stdout or "").strip()
        data: dict = {"ok": result.returncode == 0, "workflow": workflow, "exit_code": result.returncode}
        if output:
            try:
                data["result"] = json.loads(output)
            except json.JSONDecodeError:
                start = output.rfind('\n{')
                candidate = output[start + 1:] if start >= 0 else output
                try:
                    data["result"] = json.loads(candidate)
                    data["stdout_tail"] = output[:start].strip()[-2000:] if start >= 0 else ""
                except json.JSONDecodeError:
                    data["stdout"] = output[-6000:]
        if result.stderr:
            data["stderr"] = result.stderr[-3000:]
        return data

    def _sse(self, data: str) -> bool:
        """Write one SSE message. Returns False if the connection broke."""
        try:
            line = data.replace("\n", " ").replace("\r", "")
            self.wfile.write(f"data: {line}\n\n".encode("utf-8"))
            self.wfile.flush()
            return True
        except Exception:
            return False

    def _sse_event(self, item: dict) -> bool:
        """Write one typed SSE event."""
        try:
            event_type = item["event"]
            payload = json.dumps(item["data"], ensure_ascii=False)
            self.wfile.write(f"event: {event_type}\ndata: {payload}\n\n".encode("utf-8"))
            self.wfile.flush()
            return True
        except Exception:
            return False

    # ── /api/ask ────────────────────────────────────────────────

    def _api_ask(self) -> None:
        """Handle POST /api/ask — deterministic Q&A against the desk."""
        body = self._read_json_body()
        question = (body.get("question") or "").strip()
        if not question:
            self._json({"error": "question is required"}, 400)
            return
        try:
            sys.path.insert(0, str(APP_DIR))
            from agent.query import load_desk, ask
            desk = load_desk()
            answer = ask(question, desk)
            self._json({
                "question": question,
                "answer": answer,
                "engine": "deterministic",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
        except FileNotFoundError as exc:
            self._json({"error": str(exc)}, 503)
        except Exception as exc:
            self._json({"error": str(exc)}, 500)

    # ── /api/validation-packs ──────────────────────────────────

    def _api_validation_packs_index(self) -> None:
        """Serve the validation packs index."""
        index_path = APP_DIR / "outbox" / "validation_packs" / "index.json"
        if not index_path.exists():
            self._json({"error": "No validation packs index found — run the pipeline first."}, 404)
            return
        try:
            self._json(json.loads(index_path.read_text(encoding="utf-8")))
        except Exception as exc:
            self._json({"error": str(exc)}, 500)

    def _api_validation_pack(self, signal_id: str) -> None:
        """Serve a single validation pack by signal_id."""
        # Sanitize path segment — reject traversal attempts
        if "/" in signal_id or ".." in signal_id:
            self._json({"error": "Invalid signal_id"}, 400)
            return
        pack_path = APP_DIR / "outbox" / "validation_packs" / f"{signal_id}.json"
        if not pack_path.exists():
            self._json({"error": f"Validation pack '{signal_id}' not found"}, 404)
            return
        try:
            self._json(json.loads(pack_path.read_text(encoding="utf-8")))
        except Exception as exc:
            self._json({"error": str(exc)}, 500)

    # ── /api/tools.json ────────────────────────────────────────

    def _api_community_brief(self) -> None:
        """Serve the community brief (plain-language signals)."""
        brief_path = APP_DIR / "outbox" / "community_brief.md"
        if not brief_path.exists():
            self._json({"error": "Community brief not generated yet — run the pipeline first."}, 404)
            return
        try:
            content = brief_path.read_text(encoding="utf-8")
            self._json({"ok": True, "brief": content})
        except Exception as exc:
            self._json({"error": str(exc)}, 500)

    def _api_community_brief_snippets(self) -> None:
        """Serve platform-specific social snippets (X thread, Instagram, WhatsApp)."""
        snippets = {}
        for name in ("x_thread", "instagram_caption", "whatsapp_forward"):
            path = APP_DIR / "outbox" / f"community_brief_{name}.md"
            if path.exists():
                snippets[name] = path.read_text(encoding="utf-8")
        if not snippets:
            self._json({"error": "Snippets not generated yet — run the pipeline first."}, 404)
            return
        self._json({"ok": True, "snippets": snippets})

    def _api_tools_manifest(self) -> None:
        """Serve the machine-readable tool manifest."""
        self._json(TOOLS_MANIFEST)

    # ── Static file serving for discovery ──────────────────────

    def _serve_static(self, filename: str) -> None:
        """Serve a static file from the repo root (for llms.txt, agents.md)."""
        file_path = APP_DIR / filename
        if not file_path.exists():
            self.send_error(404)
            return
        try:
            content = file_path.read_text(encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8" if filename.endswith(".txt") else "text/markdown; charset=utf-8")
            self.send_header("Content-Length", str(len(content.encode("utf-8"))))
            self._cors()
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except Exception:
            self.send_error(500)

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

    # ── /api/domains/create ────────────────────────────────────

    def _api_create_domain(self) -> None:
        """Create a new blueprint domain from the UI wizard.

        This is the abstraction made interactive: a new domain is a config
        file. Writes are sanitised hard (public endpoint) — slug-only ids,
        status forced to blueprint, length caps, and a cap on UI-created
        domains so the folder can't be flooded."""
        import re as _re
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, json.JSONDecodeError):
            self._json({"ok": False, "error": "Invalid JSON body"}, 400)
            return

        name = str(body.get("name", "")).strip()[:60]
        if len(name) < 3:
            self._json({"ok": False, "error": "Name must be at least 3 characters"}, 400)
            return

        slug = _re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if len(slug) > 32:  # trim on a word boundary, not mid-word
            slug = slug[:32].rsplit("-", 1)[0] if "-" in slug[:32] else slug[:32]
        if not _re.fullmatch(r"[a-z0-9][a-z0-9-]{1,31}", slug):
            self._json({"ok": False, "error": "Name must contain letters or digits"}, 400)
            return

        domains_dir = APP_DIR / "domains"
        user_files = list(domains_dir.glob("user-*.json"))
        if len(user_files) >= 12:
            self._json({"ok": False, "error": "Product limit reached (12 user domains). Remove some first."}, 429)
            return

        target = domains_dir / f"user-{slug}.json"
        if target.exists():
            self._json({"ok": False, "error": f"A domain '{slug}' already exists"}, 409)
            return

        def _clip(key: str, fallback: str) -> str:
            return (str(body.get(key, "")).strip() or fallback)[:240]

        manifest = {
            "id": slug,
            "name": name,
            "status": "blueprint",
            "created_via": "ui",
            "tagline": _clip("tagline", "User-defined domain on the Signal Fabric engine."),
            "blurb": _clip("tagline", "User-defined domain — same engine, new sources."),
            "pipeline": {
                "watch": _clip("watch", "Public data sources for this domain."),
                "reason": _clip("reason", "Detect the signals that matter for this domain."),
                "distribute": _clip("distribute", "Route briefings to this domain's recipients."),
            },
            "sources": [],
            "signals": {"kinds": []},
            "recipients": {"personas": []},
        }

        try:
            sys.path.insert(0, str(APP_DIR))
            from domains.registry import _validate, summarise
            errs = _validate(manifest, target)
            if errs:
                self._json({"ok": False, "error": "; ".join(errs)}, 400)
                return
            target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            self._json({"ok": True, "domain": summarise(manifest)})
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    # ── /api/delivery + /api/history + /api/feedback ─────────────

    def _api_feedback_apply(self) -> None:
        try:
            self._json(self._run_node_workflow("apply-feedback", {}, timeout=60))
        except subprocess.TimeoutExpired:
            self._json({"ok": False, "error": "Timeout applying feedback"}, 504)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    def _api_delivery_approvals(self) -> None:
        p = APP_DIR / "data" / "approvals" / "delivery_approvals.json"
        if not p.exists():
            self._json({"ok": True, "approvals": []})
            return
        try:
            self._json({"ok": True, **json.loads(p.read_text())})
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    def _api_delivery_prepare(self) -> None:
        try:
            self._json(self._run_node_workflow("prepare-delivery", self._read_json_body(), timeout=60))
        except subprocess.TimeoutExpired:
            self._json({"ok": False, "error": "Timeout preparing delivery"}, 504)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    def _api_delivery_approve(self) -> None:
        body = self._read_json_body()
        if not body.get("approvalId"):
            self._json({"ok": False, "error": "approvalId required"}, 400)
            return
        try:
            self._json(self._run_node_workflow("approve-delivery", body, timeout=60))
        except subprocess.TimeoutExpired:
            self._json({"ok": False, "error": "Timeout approving delivery"}, 504)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    def _api_delivery_send_approved(self) -> None:
        body = self._read_json_body()
        if not body.get("approvalId"):
            self._json({"ok": False, "error": "approvalId required"}, 400)
            return
        # Product safety: dry-run unless explicitly set false in the JSON body.
        body["dryRun"] = body.get("dryRun", True)
        try:
            self._json(self._run_node_workflow("send-approved", body, timeout=90))
        except subprocess.TimeoutExpired:
            self._json({"ok": False, "error": "Timeout sending approved delivery"}, 504)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    def _api_history(self) -> None:
        p = APP_DIR / "data" / "history" / "index.json"
        if not p.exists():
            self._json({"ok": True, "cycles": []})
            return
        try:
            self._json({"ok": True, **json.loads(p.read_text())})
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    def _api_history_archive(self) -> None:
        try:
            payload = self._read_json_body()
            payload.setdefault("action", "archive")
            self._json(self._run_node_workflow("cycle-history", payload, timeout=60))
        except subprocess.TimeoutExpired:
            self._json({"ok": False, "error": "Timeout archiving cycle"}, 504)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    # ── /api/reasoning ─────────────────────────────────────────

    def _api_reasoning(self) -> None:
        """Serve the reasoning agent's cross-signal synthesis."""
        p = APP_DIR / "outbox" / "reasoning.json"
        if not p.exists():
            self._json({"ok": False, "error": "No synthesis yet — run the pipeline."}, 503)
            return
        try:
            self._json({"ok": True, **json.loads(p.read_text())})
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    # ── /api/track-record ───────────────────────────────────────

    def _api_track_record(self) -> None:
        """Serve the desk's public track record of cycles, responses, and priorities."""
        p = APP_DIR / "outbox" / "track_record.json"
        if not p.exists():
            self._json({"ok": False, "error": "Track record not generated yet — run the pipeline."}, 503)
            return
        try:
            self._json({"ok": True, **json.loads(p.read_text())})
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, 500)

    # ── /api/map-data + /api/status ────────────────────────────

    def _api_map_data(self) -> None:
        """Serve one current signal summary for every watched country."""
        from map_data import build_map_data

        self._json(build_map_data(APP_DIR))

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

        # Feedback outcomes — proof the system changes decisions, not just
        # produces signals.
        feedback: dict = {}
        fb_p = APP_DIR / "data" / "feedback" / "state.json"
        if fb_p.exists():
            try:
                hist = json.loads(fb_p.read_text()).get("history", [])
                for e in hist:
                    s = e.get("feedback_status", "unknown")
                    feedback[s] = feedback.get(s, 0) + 1
            except Exception:
                pass

        # Autonomous cycle count (incremented by the pipeline loop)
        cycle_count = 0
        last_cycle_time = None
        cc_p = APP_DIR / "data" / ".cycle_count.json"
        if cc_p.exists():
            try:
                cc_data = json.loads(cc_p.read_text())
                cycle_count = int(cc_data.get("count", 0))
                last_cycle_time = cc_data.get("last_run")
            except Exception:
                pass
        
        # Cycle timing for countdown
        cadence_seconds = 4 * 3600  # 4 hours
        next_cycle_in = None
        last_cycle_ago = None
        if last_cycle_time:
            try:
                from dateutil import parser as dateparser
                last_dt = dateparser.isoparse(last_cycle_time)
                now = datetime.now(timezone.utc)
                elapsed = (now - last_dt).total_seconds()
                last_cycle_ago = int(elapsed)
                remaining = cadence_seconds - elapsed
                if remaining > 0:
                    next_cycle_in = int(remaining)
                else:
                    next_cycle_in = 0
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
            "cadence_hours": 4,
            "cycle_count": cycle_count,
            "feedback": feedback,
            "live_instances": 2,
            "pipeline_running": _pipeline_running,
            "last_lines": _last_pipeline_lines[-8:],
            "server_time": datetime.now(timezone.utc).isoformat(),
            "next_cycle_in": next_cycle_in,
            "last_cycle_ago": last_cycle_ago,
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
        domain    = qs.get("domain",   ["caribbean"])[0].lower().strip()

        # Each live instance has its own dispatch desk. Climate is the
        # second live instance (hazard data → insurer/resilience roles).
        DESK_FILES = {
            "caribbean": "dispatch_desk.json",
            "climate":   "climate_desk.json",
        }
        desk_file = DESK_FILES.get(domain, "dispatch_desk.json")

        desk: dict = {}
        desk_p = APP_DIR / "outbox" / desk_file
        if desk_p.exists():
            try:
                desk = json.loads(desk_p.read_text())
            except Exception:
                pass

        clusters = desk.get("clusters", [])
        if not clusters:
            self._json({"ok": False, "error": f"No signal data yet for '{domain}' — run the pipeline first."}, 503)
            return

        fallback = False
        fallback_reason = ""
        working = clusters

        # Country/signal filters are economic concepts; for non-economic
        # instances (climate) we route by strongest live hazard instead.
        if domain != "caribbean":
            countries = ["all"]
            signals = ["all"]

        # ── Country filter ─────────────────────────────────────
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
        if domain == "climate":
            # Map the economic role chips onto the climate instance's roles
            PERSONA_TERMS = {
                "investor":  ["insurer", "reinsurer"],
                "founder":   ["operations", "resilience", "operator"],
                "policy":    ["resilience planner", "planner"],
                "diaspora":  ["insurer"],
            }
        else:
            PERSONA_TERMS = {
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

        # For the climate instance, use the dispatch's own recipient label
        if domain == "climate":
            persona_label = persona_rec.get("persona", "Resilience Planner") if persona_rec else "Resilience Planner"
        else:
            PERSONA_DISPLAY = {
                "investor": "Diaspora Investor",
                "founder":  "Regional Founder / Operator",
                "policy":   "Policy / Media",
                "diaspora": "Diaspora",
            }
            persona_label = PERSONA_DISPLAY.get(persona, persona.title())

        # Domain-specific framing
        if domain == "climate":
            is_all_clear = cluster.get("signal_kind") == "all_clear"
            if is_all_clear:
                head_title = "Caribbean Conditions — All Clear"
                head_emoji = "🌤️"
                head_name = "Caribbean Conditions"
            else:
                head_title = "Caribbean Hazard Alert"
                head_emoji = "🌀"
                head_name = "Caribbean Hazard Signal"
            source_label = "NOAA NWS / NDBC buoys / NHC outlook"
            disclaimer = "Decision-support signal. Always follow official emergency directives."
        else:
            head_title = "Caribbean Opportunity Signal"
            head_emoji = "🌴"
            head_name = "Caribbean Signal"
            source_label = "World Bank / IDB / NOAA / CARICOM / CDB"
            disclaimer = "Screening signal only. Not investment advice."

        # ── Format per channel ──────────────────────────────────
        pct_str = f" ({pct})" if pct else ""

        if channel == "telegram":
            formatted = (
                f"*{head_title}*\n\n"
                f"*{country}* — {confidence}\n\n"
                f"{evidence}{pct_str}\n\n"
                f"*What to do ({persona_label}):*\n{action}\n\n"
                + (f"⚠️ Risk flag: {risks[0]}\n\n" if risks else "")
                + f"_{disclaimer}_"
            )
        elif channel == "whatsapp":
            formatted = (
                f"{head_emoji} {head_name}\n\n"
                f"{country}: {evidence}{pct_str}\n\n"
                f"{action[:160]}\n\n"
                f"{disclaimer}\n"
                f"Full brief: https://future-caribbean.fly.dev"
            )
        elif channel == "email":
            kind_word = "hazard" if domain == "climate" else "market"
            formatted = (
                f"Subject: {country} — {confidence.lower()} {kind_word} signal\n\n"
                f"{evidence}{pct_str}\n\n"
                f"For {persona_label}:\n{action}\n\n"
                + (f"Risk flag: {risks[0]}\n\n" if risks else "")
                + f"Source: {source_label}\nConfidence: {confidence}\n\n"
                f"{disclaimer}\n"
                f"Caribbean Opportunity Dispatch"
            )
        else:  # memo
            brief_title = "CARIBBEAN HAZARD BRIEF" if domain == "climate" else "CARIBBEAN OPPORTUNITY BRIEF"
            loc_label = "Area" if domain == "climate" else "Country"
            formatted = (
                f"{brief_title}\n"
                f"{'─' * 36}\n"
                f"{loc_label}:      {country}\n"
                f"Confidence: {confidence}\n"
                f"Audience:   {persona_label}\n\n"
                f"SIGNAL\n{evidence}{pct_str}\n\n"
                f"RECOMMENDED ACTION\n{action}\n\n"
                + (f"RISK FLAG\n{risks[0]}\n\n" if risks else "")
                + f"{'─' * 36}\n"
                f"{disclaimer}\n"
                f"Caribbean Opportunity Dispatch"
            )

        self._json({
            "ok":             True,
            "domain":         domain,
            "persona":        persona_label,
            "channel":        channel,
            "country":        country,
            "confidence":     confidence,
            "evidence":       evidence,
            "pct":            pct,
            "action":         action,
            "source":         source_label,
            "risks":          risks[:1],
            "formatted":      formatted,
            "fallback":       fallback,
            "fallback_reason": fallback_reason,
            "freshness":      cluster.get("freshness", ""),
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

    def _api_pipeline_stream(self, replay: bool = False) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self._cors()
        self.end_headers()

        if replay:
            from pipeline_events import latest_history, synthetic_events

            events = latest_history(APP_DIR) or synthetic_events(APP_DIR)
            previous_ts: float | None = None
            for item in events:
                ts = float(item.get("data", {}).get("ts", time.time()))
                if previous_ts is not None:
                    time.sleep(min(max((ts - previous_ts) / 10, 0), 1))
                if not self._sse_event(item):
                    break
                previous_ts = ts
            return

        subscriber: queue.Queue = queue.Queue()
        with _pipeline_subscribers_lock:
            _pipeline_subscribers.add(subscriber)
        _start_pipeline_cycle_if_idle()
        try:
            while True:
                try:
                    item = subscriber.get(timeout=15)
                    if not self._sse_event(item):
                        break
                except queue.Empty:
                    try:
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
                    except Exception:
                        break
        finally:
            with _pipeline_subscribers_lock:
                _pipeline_subscribers.discard(subscriber)

    # ── /api/webhooks ──────────────────────────────────────────

    def _api_webhooks_list(self) -> None:
        from packagers.webhook_notifier import list_subscriptions
        subs = list_subscriptions()
        self._json({"ok": True, "subscriptions": subs, "count": len(subs)})

    def _api_webhooks_subscribe(self) -> None:
        from packagers.webhook_notifier import create_subscription
        body = self._read_json_body()
        url = body.get("url", "").strip()
        if not url or not url.startswith("http"):
            self._json({"ok": False, "error": "url required (must start with http)"}, 400)
            return
        threshold = int(body.get("threshold", 80))
        if not (0 <= threshold <= 100):
            self._json({"ok": False, "error": "threshold must be 0–100"}, 400)
            return
        sub = create_subscription(
            url=url,
            threshold=threshold,
            country=body.get("country") or None,
            signal_kind=body.get("signal_kind") or None,
        )
        self._json({"ok": True, "subscription": sub})

    def _api_webhooks_delete(self, sub_id: str) -> None:
        from packagers.webhook_notifier import delete_subscription
        deleted = delete_subscription(sub_id.strip())
        if deleted:
            self._json({"ok": True, "deleted": sub_id})
        else:
            self._json({"ok": False, "error": f"subscription {sub_id!r} not found"}, 404)

    def list_directory(self, path):
        self.send_error(404)
        return None

    def log_message(self, format, *args):
        pass


def _run_pipeline_cycle(emit=None) -> list[dict]:
    """Run one real pipeline cycle, emit typed events, and persist its replay."""
    global _last_pipeline_lines
    from pipeline_events import append_history, cycle_number, outbox_events, source_event_from_line

    _last_pipeline_lines = []
    events: list[dict] = []
    proc = subprocess.Popen(
        ["bash", "run_pipeline.sh"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=str(APP_DIR),
    )
    for raw in proc.stdout:  # type: ignore[union-attr]
        line = raw.rstrip()
        if not line:
            continue
        _last_pipeline_lines.append(line)
        if len(_last_pipeline_lines) > 80:
            _last_pipeline_lines = _last_pipeline_lines[-80:]
        item = source_event_from_line(line)
        if item:
            events.append(item)
            if emit:
                emit(item)
    proc.wait()

    for item in outbox_events(APP_DIR, cycle_number(APP_DIR)):
        events.append(item)
        if emit:
            emit(item)
    append_history(APP_DIR, events)
    _bump_cycle_count()
    return events


def _broadcast_event(item: dict) -> None:
    """Publish a typed pipeline event to every connected live stream."""
    with _pipeline_subscribers_lock:
        subscribers = list(_pipeline_subscribers)
    for subscriber in subscribers:
        subscriber.put(item)


def _pipeline_cycle_worker() -> None:
    global _pipeline_running
    try:
        _run_pipeline_cycle(_broadcast_event)
    except Exception as exc:
        from pipeline_events import event
        _broadcast_event(event("cycle_complete", cycle=0, signals=0, error=str(exc)))
    finally:
        _pipeline_running = False
        _pipeline_lock.release()


def _start_pipeline_cycle_if_idle() -> bool:
    """Start a broadcast cycle without racing another live or scheduled cycle."""
    global _pipeline_running
    if not _pipeline_lock.acquire(blocking=False):
        return False
    _pipeline_running = True
    threading.Thread(target=_pipeline_cycle_worker, daemon=True).start()
    return True


def _bump_cycle_count() -> None:
    """Record one completed autonomous cycle."""
    cc_p = APP_DIR / "data" / ".cycle_count.json"
    count = 0
    if cc_p.exists():
        try:
            count = int(json.loads(cc_p.read_text()).get("count", 0))
        except Exception:
            count = 0
    try:
        cc_p.parent.mkdir(parents=True, exist_ok=True)
        cc_p.write_text(json.dumps({
            "count": count + 1,
            "last_run": datetime.now(timezone.utc).isoformat(),
        }) + "\n", encoding="utf-8")
    except Exception:
        pass


def pipeline_loop():
    """Run the pipeline on startup and every 4 hours."""
    time.sleep(3)
    while True:
        global _pipeline_running
        with _pipeline_lock:
            _pipeline_running = True
            try:
                _run_pipeline_cycle(_broadcast_event)
            finally:
                _pipeline_running = False
        time.sleep(14400)


if __name__ == "__main__":
    if os.environ.get("DISABLE_PIPELINE_LOOP") != "1":
        threading.Thread(target=pipeline_loop, daemon=True).start()
    os.chdir(str(APP_DIR))
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), AppHandler)
    print(f"Listening on :{PORT}")
    server.serve_forever()
