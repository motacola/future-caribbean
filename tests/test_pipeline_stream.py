"""Tests for typed pipeline SSE history and replay."""
from __future__ import annotations

import threading
import urllib.request
from datetime import datetime, timezone

import server
import pipeline_events
from pipeline_events import event, record_cycle_events


def _replay_request(root):
    original_root = server.APP_DIR
    server.APP_DIR = root
    httpd = server.http.server.ThreadingHTTPServer(("127.0.0.1", 0), server.AppHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{httpd.server_port}/api/pipeline/stream?replay=1",
            timeout=5,
        ) as response:
            return response.status, response.headers, response.read().decode("utf-8")
    finally:
        httpd.shutdown()
        httpd.server_close()
        server.APP_DIR = original_root


def test_pipeline_stream_endpoint_exists(tmp_path):
    record_cycle_events(tmp_path)
    status, headers, body = _replay_request(tmp_path)
    assert status == 200
    assert headers.get_content_type() == "text/event-stream"
    assert "event: source_check" in body


def test_history_file_written_after_cycle(tmp_path, monkeypatch):
    class FakeProcess:
        stdout = iter(["--- World Bank ---\n", "  ✓ World Bank\n"])

        def wait(self):
            return 0

    monkeypatch.setattr(server, "APP_DIR", tmp_path)
    monkeypatch.setattr(server.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setattr(
        pipeline_events,
        "outbox_events",
        lambda root, cycle: [event("cycle_complete", cycle=cycle, signals=0)],
    )

    server._run_pipeline_cycle()
    today = datetime.now(timezone.utc).date().isoformat()
    path = tmp_path / "data" / "history" / f"{today}.jsonl"
    assert path.exists()
    assert "source_check" in path.read_text()
    assert "cycle_complete" in path.read_text()


def test_replay_mode_returns_events(tmp_path):
    record_cycle_events(tmp_path)
    _, _, body = _replay_request(tmp_path)
    assert body.count("event: ") >= 1
    assert "event: cycle_complete" in body
