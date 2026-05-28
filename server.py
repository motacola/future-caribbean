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


def pipeline_loop():
    """Run the pipeline every 4 hours."""
    # Run once on startup
    subprocess.run(["bash", "run_pipeline.sh"], capture_output=True, cwd=str(APP_DIR))
    while True:
        time.sleep(14400)  # 4 hours
        subprocess.run(["bash", "run_pipeline.sh"], capture_output=True, cwd=str(APP_DIR))


if __name__ == "__main__":
    # Start pipeline in background
    t = threading.Thread(target=pipeline_loop, daemon=True)
    t.start()

    # Serve static files
    os.chdir(str(APP_DIR))
    server = http.server.HTTPServer(("0.0.0.0", PORT), http.server.SimpleHTTPRequestHandler)
    print(f"Serving on port {PORT}")
    server.serve_forever()
