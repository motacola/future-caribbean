"""Vercel serverless function: GET /api/community-brief[?format=<snippets|x_thread|instagram|whatsapp>]"""
import json
import re
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTBOX = ROOT / "outbox"

_CYCLE_RE = re.compile(r"Cycle\s+(\d{8})")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return ""


def _cycle(text: str) -> str | None:
    m = _CYCLE_RE.search(text)
    return m.group(1) if m else None


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
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        fmt = (qs.get("format", [None])[0] or "").lower()

        main = _read(OUTBOX / "community_brief.md")
        snippets = {
            "x_thread": _read(OUTBOX / "community_brief_x_thread.md"),
            "instagram": _read(OUTBOX / "community_brief_instagram_caption.md"),
            "whatsapp": _read(OUTBOX / "community_brief_whatsapp_forward.md"),
        }
        cycle = _cycle(main)

        if fmt in snippets:
            self._json({
                "ok": True,
                "format": fmt,
                "cycle": cycle,
                "text": snippets[fmt],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
        elif fmt == "snippets":
            self._json({
                "ok": True,
                "cycle": cycle,
                "snippets": snippets,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
        else:
            self._json({
                "ok": True,
                "cycle": cycle,
                "text": main,
                "snippets": snippets,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
