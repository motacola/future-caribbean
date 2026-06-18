"""Tender watcher runner — merges national portal adapters into latest.json."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from watchers.tenders import ADAPTERS
from watchers.tenders.base import merge_records, write_latest


def main() -> None:
    items = merge_records(ADAPTERS)
    dest = write_latest(items)
    print(f"tenders: {len(items)} live records -> {dest}")


if __name__ == "__main__":
    main()
