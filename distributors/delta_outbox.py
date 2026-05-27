#!/usr/bin/env python3
"""Delta distributor for packaged outbox deliverables.

Tracks the content hash of each outbox file. Outputs changed content
to stdout for cron delivery. Silent when nothing has changed.

Used by the full-pipeline cron job to deliver only-new Telegram digests,
investor briefs, and diaspora posts.
"""

from __future__ import annotations

import logging
import json
import hashlib
import os
import tempfile
from pathlib import Path

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "data" / "outbox" / ".sent_digests.json"
OUTBOX_DIR = ROOT / "outbox"

# Files to track for delivery — in priority order
TRACKED_FILES = [
    "telegram_digest.md",
    "investor_brief.md",
    "diaspora_post.md",
]


def file_hash(path: Path) -> str:
    """SHA-256 content hash of a file."""
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_state() -> dict[str, str]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            LOGGER.warning("json/state file read error")
    return {}


def save_state(state: dict[str, str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STATE_FILE.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(state, indent=2) + "\n")
        os.replace(tmp, STATE_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            LOGGER.warning("state file write error")
        raise


def run() -> int:
    state = load_state()
    changed_count = 0

    for filename in TRACKED_FILES:
        filepath = OUTBOX_DIR / filename
        if not filepath.exists():
            continue

        current_hash = file_hash(filepath)
        last_hash = state.get(filename, "")

        if current_hash and current_hash != last_hash:
            # File has changed — output its content for delivery
            content = filepath.read_text(encoding="utf-8").strip()
            if content:
                print(f"📬 {filename}", flush=True)
                print("", flush=True)
                print(content, flush=True)
                print("", flush=True)
                print("---", flush=True)
                print("", flush=True)
                changed_count += 1
            state[filename] = current_hash

    if changed_count == 0:
        # No new deliverables — silent exit (no Telegram message)
        pass

    save_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
