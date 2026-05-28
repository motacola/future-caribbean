#!/usr/bin/env python3
"""Serve dashboard and run pipeline on a schedule."""

import http.server
import os
import subprocess
import threading
import time
from pathlib import Path

PORT = int(os.environ.get("PORT", 8080))
APP_DIR = Path(__file__).parent

# Paths that should never be served
BLOCKED_PREFIXES = (
    ".git", ".env", ".claude", ".hermes", ".ruff_cache",
    "data/", "signals/", "watchers/", "mergers/", "distributors/",
    "packagers/", "planning/", "tests/", "agent/", "architecture/",
    "run_pipeline.sh", "requirements.txt", "server.py", "Dockerfile",
    "Procfile", "fly.toml", "vercel.json", ".gitignore",
)


class SecureHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0].lstrip("/")

        # Block access to internal/sensitive paths
        for blocked in BLOCKED_PREFIXES:
            if path.startswith(blocked) or path == blocked:
                self.send_error(404, "Not found")
                return

        # Redirect root to dashboard
        if path == "" or path == "index.html":
            self.path = "/dashboard.html"

        return super().do_GET()

    def list_directory(self, path):
        """Disable directory listing entirely."""
        self.send_error(404, "Not found")
        return None


def pipeline_loop():
    """Run the pipeline every 4 hours."""
    subprocess.run(["bash", "run_pipeline.sh"], capture_output=True, cwd=str(APP_DIR))
    while True:
        time.sleep(14400)
        subprocess.run(["bash", "run_pipeline.sh"], capture_output=True, cwd=str(APP_DIR))


if __name__ == "__main__":
    t = threading.Thread(target=pipeline_loop, daemon=True)
    t.start()
    os.chdir(str(APP_DIR))
    server = http.server.HTTPServer(("0.0.0.0", PORT), SecureHandler)
    print(f"Serving on port {PORT}")
    server.serve_forever()
