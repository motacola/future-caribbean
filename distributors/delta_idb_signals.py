#!/usr/bin/env python3
"""Extract new/updated IDB dataset signals since last run.

Same pattern as distributors/delta_signals.py but reads from
signals/idb/latest.md and tracks by dataset fingerprint.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNAL_FILE = ROOT / "signals" / "idb" / "latest.md"
STATE_FILE = ROOT / "data" / "idb" / ".sent_deltas.json"


def extract_new_datasets(text: str) -> list[str]:
    """Parse the ## New Datasets section from the IDB signal brief."""
    lines = text.splitlines()
    in_section = False
    datasets: list[str] = []
    buffer: list[str] = []
    for line in lines:
        if line.strip() == "## New Datasets":
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            if line.startswith("- *"):
                if buffer:
                    datasets.append("\n".join(buffer))
                buffer = [line[2:]]
            elif line.startswith("  ") and buffer:
                buffer.append(line.strip())
            else:
                if buffer:
                    datasets.append("\n".join(buffer))
                    buffer = []
    if buffer:
        datasets.append("\n".join(buffer))
    return datasets


def extract_updated_datasets(text: str) -> list[str]:
    """Parse the ## Recently Updated Datasets section."""
    lines = text.splitlines()
    in_section = False
    datasets: list[str] = []
    buffer: list[str] = []
    for line in lines:
        if line.strip() == "## Recently Updated Datasets":
            in_section = True
            continue
        if in_section:
            if line.startswith("## ") or line.startswith("**"):
                break
            if line.startswith("- *"):
                if buffer:
                    datasets.append("\n".join(buffer))
                buffer = [line[2:]]
            elif line.startswith("  ") and buffer:
                buffer.append(line.strip())
            else:
                if buffer:
                    datasets.append("\n".join(buffer))
                    buffer = []
    if buffer:
        datasets.append("\n".join(buffer))
    return datasets


def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_state(fingerprints: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(fingerprints), indent=2) + "\n", encoding="utf-8")


def fingerprint(dataset_text: str) -> str:
    """Stable fingerprint from the dataset title line."""
    m = re.search(r"\*([^*]+)\*", dataset_text)
    if m:
        return m.group(1).strip().lower()[:80]
    return dataset_text.strip()[:80].lower()


def extract_summary_line(dataset_text: str) -> str:
    """Get the first line (title + badges)."""
    return dataset_text.split("\n")[0] if dataset_text else ""


def main() -> int:
    if not SIGNAL_FILE.exists():
        print("No IDB signal file yet. Run the poller first.", file=sys.stderr)
        return 1

    text = SIGNAL_FILE.read_text(encoding="utf-8")
    new = extract_new_datasets(text)
    updated = extract_updated_datasets(text)

    if not new and not updated:
        return 0

    state = load_state()
    all_new_lines: list[str] = []
    new_fingerprints: set[str] = set()

    now = datetime.now(timezone.utc).strftime("%b %d, %Y at %H:%M UTC")

    # Check new datasets
    for ds in new:
        fp = fingerprint(ds)
        if fp not in state:
            new_fingerprints.add(fp)
            all_new_lines.append(f"  • {extract_summary_line(ds)}")

    # Check updated datasets  
    for ds in updated:
        fp = fingerprint(ds)
        if fp not in state:
            new_fingerprints.add(fp)
            all_new_lines.append(f"  • {extract_summary_line(ds)} (updated)")

    if not all_new_lines:
        return 0

    # Output in Telegram-friendly markdown
    print(f"*IDB Caribbean Dataset Signals — {now}*")
    print()
    if new:
        print("*New datasets available:*")
        print()
        for line in new:
            print(line)
        print()
    if updated:
        print("*Recently updated datasets:*")
        print()
        up_lines = [line for line in all_new_lines if line.endswith("(updated)")]
        for line in up_lines:
            print(line)
        print()
    print("— Abeng • IDB watcher")

    # Update state with all current fingerprints (including ones already sent)
    all_current = {fingerprint(ds) for ds in new + updated}
    save_state(state | all_current)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
