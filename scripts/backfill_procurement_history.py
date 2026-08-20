#!/usr/bin/env python3
"""Rebuild the canonical procurement corpus from the raw snapshot archive.

`data/tenders/latest.json` only ever holds the last poll, so a corpus
started from it would date every tender to today and no detection lead
time could be proved. `data/tenders/raw/` has kept dated GOJEP HTML
snapshots since June, and the adapter's parsers are pure functions over
that HTML — so replaying the archive in date order reconstructs when each
tender was actually first seen, when its closing date moved, and when its
award notice appeared.

Deterministic and non-destructive: same archive in, same corpus out. Run
with --dry-run to inspect without writing.

    python3 scripts/backfill_procurement_history.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from resolvers import procurement as proc  # noqa: E402
from watchers.tenders.guyana_eprocure import parse_guyana_records  # noqa: E402
from watchers.tenders.idb_procurement import parse_idb_notices  # noqa: E402
from watchers.tenders.jamaica_gojep import (  # noqa: E402
    parse_award_notices_html,
    parse_opened_tenders_html,
)

RAW = ROOT / "data" / "tenders" / "raw"

# snapshot slug -> (file extension, parser for that feed)
PARSERS = {
    "jamaica-gojep-opened": ("html", parse_opened_tenders_html),
    "jamaica-gojep-awards": ("html", parse_award_notices_html),
    "guyana-eprocure": ("json", lambda text: parse_guyana_records(json.loads(text))),
    # One dated CSV covering years of IDB notices. Every row enters at the
    # snapshot date rather than its own publication date: the corpus records
    # when this desk first had the data, and backdating it to when IDB
    # published would claim detections we never made.
    "idb-procurement": ("csv", parse_idb_notices),
}

_STAMP = re.compile(r"-(\d{8})\.(?:html|json|csv)$")


def snapshot_date(path: Path) -> str | None:
    m = _STAMP.search(path.name)
    if not m:
        return None
    stamp = m.group(1)
    return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}"


def replay(raw_dir: Path = RAW) -> tuple[dict, list[str]]:
    """Fold every archived snapshot into a fresh corpus, oldest first."""
    snapshots: list[tuple[str, Path, str]] = []
    for slug, (ext, _parser) in PARSERS.items():
        for path in raw_dir.glob(f"{slug}-*.{ext}"):
            day = snapshot_date(path)
            if day:
                snapshots.append((day, path, slug))
    # Chronological, with opportunity feeds ahead of award feeds on the same
    # day so an award has a detection to attach to.
    snapshots.sort(key=lambda s: (s[0], "awards" in s[2], s[1].name))

    corpus = {"schema_version": proc.SCHEMA_VERSION, "tenders": {}}
    log: list[str] = []
    for day, path, slug in snapshots:
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            records = PARSERS[slug][1](text) if text.strip() else []
        except (json.JSONDecodeError, ValueError) as exc:
            log.append(f"{day} {path.name}: unparseable ({exc})")
            continue
        if not records:
            log.append(f"{day} {path.name}: no records parsed")
            continue
        # Observation time is the snapshot's own date, not now — otherwise
        # every historical tender would claim to have been detected today.
        observed_at = f"{day}T00:00:00+00:00"
        proc.observe(records, corpus, observed_at=observed_at)
        log.append(f"{day} {path.name}: {len(records)} records")
    proc.refresh(corpus)
    corpus["updated_at"] = datetime.now(timezone.utc).isoformat()
    return corpus, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report without writing the corpus")
    args = ap.parse_args()

    corpus, log = replay()
    for line in log:
        print("  " + line)

    tenders = list(corpus["tenders"].values())
    states: dict[str, int] = {}
    for t in tenders:
        states[t["lifecycle_state"]] = states.get(t["lifecycle_state"], 0) + 1
    resolved = [t for t in tenders if t.get("resolution")]
    independence: dict[str, int] = {}
    for t in resolved:
        k = t["resolution"]["independence"]
        independence[k] = independence.get(k, 0) + 1
    with_lead = [t for t in tenders if t.get("lead_time_days") is not None]

    print()
    print(f"canonical tenders:   {len(tenders)}")
    print(f"lifecycle states:    " + ", ".join(f"{k}={v}" for k, v in sorted(states.items())))
    print(f"resolved outcomes:   {len(resolved)} ({', '.join(f'{k}={v}' for k, v in sorted(independence.items())) or 'none'})")
    print(f"amendments linked:   {sum(len(t['amendments']) for t in tenders)}")
    print(f"lead times computed: {len(with_lead)}")

    if args.dry_run:
        print("\n(dry run — corpus not written)")
        return 0
    dest = proc.save_corpus(corpus)
    print(f"\nwrote {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
