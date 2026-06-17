"""Vercel serverless function: POST /api/ask"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from http.server import BaseHTTPRequestHandler

# Resolve repo root: /var/task is Vercel's working dir, api/ is one level down
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.query import load_desk, ask  # noqa: E402

MAX_QUESTION_LEN = 500


class handler(BaseHTTPRequestHandler):
    def _json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
            return body if isinstance(body, dict) else {}
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        self._json({
            "usage": "POST {\"question\": \"...\"} to /api/ask",
            "example": {"question": "explain the lead signal"},
            "max_question_length": MAX_QUESTION_LEN,
            "engine": "deterministic",
            "note": "Answers are cited from committed Dispatch Desk artifacts — no LLM generation."
        })

    def do_POST(self):
        body = self._read_json_body()
        question = (body.get("question") or "").strip()

        if not question:
            self._json({"error": "question is required"}, 400)
            return

        if len(question) > MAX_QUESTION_LEN:
            self._json({"error": f"question exceeds {MAX_QUESTION_LEN} characters"}, 413)
            return

        try:
            desk = load_desk()
            answer = ask(question, desk)
            self._json({
                "question": question,
                "answer": answer,
                "engine": "deterministic",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
        except FileNotFoundError as exc:
            self._json({"error": str(exc), "note": "Run the pipeline to generate desk artifacts"}, 503)
        except Exception as exc:
            self._json({"error": str(exc)}, 500)