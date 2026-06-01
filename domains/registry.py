#!/usr/bin/env python3
"""Domain registry for Signal Fabric.

A *domain* is a declarative manifest (domains/*.json) that defines one
instance of the engine: which public sources it watches, which signal
rules it reasons over, and which recipients it distributes to.

The engine itself is domain-agnostic. Standing up a new instance is a
config file — not a rebuild. This module loads, validates, and lists
those manifests so the same abstraction is enforced in code and surfaced
to the UI (via /api/domains) rather than only described in copy.

CLI:
    python3 domains/registry.py            # table of all domains
    python3 domains/registry.py --json     # machine-readable
    python3 domains/registry.py --validate # exit non-zero on any error
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DOMAINS_DIR = Path(__file__).resolve().parent
REQUIRED_KEYS = ("id", "name", "status", "pipeline", "sources", "recipients")
VALID_STATUS = ("live", "blueprint")
PIPELINE_STAGES = ("watch", "reason", "distribute")


def _validate(manifest: dict[str, Any], path: Path) -> list[str]:
    """Return a list of human-readable problems (empty == valid)."""
    errs: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in manifest:
            errs.append(f"{path.name}: missing required key '{key}'")
    status = manifest.get("status")
    if status and status not in VALID_STATUS:
        errs.append(f"{path.name}: status '{status}' not in {VALID_STATUS}")
    pipe = manifest.get("pipeline", {})
    for stage in PIPELINE_STAGES:
        if stage not in pipe:
            errs.append(f"{path.name}: pipeline missing '{stage}' stage")
    if not isinstance(manifest.get("sources", []), list):
        errs.append(f"{path.name}: 'sources' must be a list")
    return errs


def load_all(validate: bool = True) -> tuple[list[dict[str, Any]], list[str]]:
    """Load every domain manifest. Returns (domains, errors).

    Live domains sort first, then alphabetical by name.
    """
    domains: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in sorted(DOMAINS_DIR.glob("*.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"{path.name}: unreadable — {exc}")
            continue
        if validate:
            errors.extend(_validate(manifest, path))
        manifest["_file"] = path.name
        domains.append(manifest)

    domains.sort(key=lambda d: (d.get("status") != "live", d.get("name", "")))
    return domains, errors


def summarise(d: dict[str, Any]) -> dict[str, Any]:
    """Compact, UI-friendly view of one domain."""
    sources = d.get("sources", [])
    wired = [s for s in sources if s.get("watcher")]
    recipients = (d.get("recipients", {}) or {}).get("personas", [])
    signals = (d.get("signals", {}) or {}).get("kinds", [])
    return {
        "id": d.get("id"),
        "name": d.get("name"),
        "status": d.get("status"),
        "blurb": d.get("blurb") or d.get("tagline", ""),
        "pipeline": d.get("pipeline", {}),
        "counts": {
            "sources": len(sources),
            "sources_wired": len(wired),
            "signals": len(signals),
            "recipients": len(recipients),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Signal Fabric domain registry")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--validate", action="store_true", help="exit non-zero on errors")
    args = ap.parse_args()

    domains, errors = load_all(validate=True)

    if args.json:
        print(json.dumps([summarise(d) for d in domains], indent=2))
    else:
        print(f"\nSignal Fabric — {len(domains)} domain(s) registered\n")
        for d in domains:
            s = summarise(d)
            tag = "● LIVE     " if s["status"] == "live" else "○ blueprint"
            c = s["counts"]
            print(f"  {tag}  {s['name']}")
            print(f"               {c['sources_wired']}/{c['sources']} sources wired · "
                  f"{c['signals']} signal rules · {c['recipients']} recipient roles")
        print()
        if errors:
            print("Validation problems:")
            for e in errors:
                print(f"  ✗ {e}")
            print()

    if args.validate and errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
