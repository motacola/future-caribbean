"""Tests for what the local full-stack server serves to a browser.

Two regressions under test.

1. Every Astro page except the home page and /build 404'd under
   `python3 server.py` — the documented way to run the full stack. Routes were
   a hand-maintained allowlist, and /accuracy, /capability-matches,
   /opportunity-resolution and /regional-connections were added to the site
   (and linked from the home page) without being added to it.

2. Opening the home page ran a pipeline cycle. The cycle theater connects to
   /api/pipeline/stream on load, and the handler started a cycle for any caller
   that opened the stream — so a page view rewrote every published artefact,
   republishing a degraded cycle over good data whenever a source was down.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import server

ROOT = Path(__file__).resolve().parents[1]


def _serve(root: Path):
    """Run the handler against `root` and return (base_url, shutdown)."""
    original = server.APP_DIR
    server.APP_DIR = root
    httpd = server.http.server.ThreadingHTTPServer(("127.0.0.1", 0), server.AppHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def shutdown():
        httpd.shutdown()
        httpd.server_close()
        server.APP_DIR = original

    return f"http://127.0.0.1:{httpd.server_port}", shutdown


def _status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


@pytest.fixture
def built_site():
    """The real repo, served the way `python3 server.py` serves it.

    dist/ is gitignored, so a checkout that has not run `pnpm build` has
    nothing to serve and the routing assertions do not apply.
    """
    if not (ROOT / "dist" / "index.html").is_file():
        pytest.skip("dist/ not built — run `pnpm build` first")
    return ROOT


def _a_built_signal_page() -> str | None:
    signal_root = ROOT / "dist" / "signal"
    if not signal_root.is_dir():
        return None
    for child in sorted(signal_root.iterdir()):
        if (child / "index.html").is_file():
            return f"/signal/{child.name}"
    return None


@pytest.mark.parametrize("path", [
    "/", "/build", "/accuracy", "/capability-matches",
    "/opportunity-resolution", "/regional-connections",
])
def test_every_built_page_is_reachable(built_site, path):
    if not (built_site / "dist" / path.strip("/") / "index.html").is_file() and path != "/":
        pytest.skip(f"{path} is not in this build")
    base, shutdown = _serve(built_site)
    try:
        assert _status(base + path) == 200, f"{path} is in dist/ but the server does not serve it"
    finally:
        shutdown()


def test_signal_permalinks_are_reachable(built_site):
    path = _a_built_signal_page()
    if path is None:
        pytest.skip("no signal pages in this build")
    base, shutdown = _serve(built_site)
    try:
        assert _status(base + path) == 200
    finally:
        shutdown()


@pytest.mark.parametrize("path", [
    "/nope",                      # no such page
    "/server.py",                 # source file
    "/data/feedback/state.json",  # internal data
    "/../etc/passwd",             # traversal
])
def test_unbuilt_and_internal_paths_stay_404(built_site, path):
    base, shutdown = _serve(built_site)
    try:
        assert _status(base + path) == 404, f"{path} must not be served"
    finally:
        shutdown()


def test_page_resolution_cannot_escape_dist(tmp_path):
    """The directory→index.html lookup must not walk out of dist/."""
    (tmp_path / "dist" / "accuracy").mkdir(parents=True)
    (tmp_path / "dist" / "accuracy" / "index.html").write_text("ok", encoding="utf-8")
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "index.html").write_text("nope", encoding="utf-8")
    original = server.APP_DIR
    server.APP_DIR = tmp_path
    try:
        assert server._astro_page_exists("accuracy") is True
        assert server._astro_page_exists("../secret") is False
        assert server._astro_page_exists("dist/../secret") is False
        assert server._astro_page_exists("/etc") is False
        assert server._astro_page_exists("") is False
    finally:
        server.APP_DIR = original


def test_opening_the_stream_does_not_start_a_cycle(tmp_path, monkeypatch):
    """Watching the theater is a read — it must not launch a pipeline run."""
    started = []
    monkeypatch.setattr(server, "_start_pipeline_cycle_if_idle",
                        lambda: started.append(True) or True)

    base, shutdown = _serve(tmp_path)
    try:
        with urllib.request.urlopen(base + "/api/pipeline/stream", timeout=5) as r:
            assert r.status == 200
            r.read(1)
    except Exception:
        pass
    finally:
        shutdown()

    assert started == [], "a page view started a pipeline cycle"


def test_explicit_run_requires_the_admin_token(tmp_path, monkeypatch):
    """?run=1 is a write. Without the token it is refused and starts nothing."""
    started = []
    monkeypatch.setattr(server, "_start_pipeline_cycle_if_idle",
                        lambda: started.append(True) or True)
    monkeypatch.setenv("DESK_ADMIN_TOKEN", "test-token")

    base, shutdown = _serve(tmp_path)
    try:
        assert _status(base + "/api/pipeline/stream?run=1") == 401
    finally:
        shutdown()

    assert started == [], "an unauthenticated request started a pipeline cycle"
