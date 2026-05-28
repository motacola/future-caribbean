#!/usr/bin/env python3
"""Serve Caribbean Opportunity Dispatch — product-first homepage."""

import http.server
import mimetypes
import os
import subprocess
import threading
import time
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


class AppHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler: redirects / to /dashboard.html, blocks internal paths."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.lstrip("/")

        # Block internal paths
        for blocked in BLOCKED_PREFIXES:
            if path == blocked or path.startswith(blocked):
                self.send_error(404)
                return

        # Root → dashboard
        if path == "" or path == "index.html":
            self.path = "/dashboard.html"

        return super().do_GET()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def log_message(self, format, *args):
        """Quieter logging."""
        pass


def pipeline_loop():
    """Run the pipeline on startup and every 4 hours."""
    time.sleep(2)  # let server start first
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
