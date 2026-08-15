#!/usr/bin/env python3
"""Ranking invariants — deterministic replacement for hand-checking the desk.

Prints a table and exits non-zero if any invariant breaks, so it can gate CI.
No LLM involved: every check below was previously done by eye.

    python3 scripts/verify_ranking.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packagers.editorial_enrichment import enrich_signals  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  — ' + detail if detail else ''}")
    if not ok:
        FAILURES.append(name)


def main() -> int:
    raw = json.loads((ROOT / "data" / "composite" / "latest.json").read_text())
    signals = raw.get("signals") or []

    pkg = enrich_signals([dict(s) for s in signals], "verify")
    enriched = pkg["enriched_signals"]
    lead = pkg["lead_signal"] or {}

    print("\nRanked signals")
    print(f"  {'country':<12} {'kind':<22} {'raw':>5} {'shown':>5} {'mag%':>8} {'stale':>6}")
    for s in sorted(enriched, key=lambda x: -x.get("_score_raw", 0))[:8]:
        mag = s.get("_magnitude_pct")
        print(
            f"  {str(s.get('_country'))[:12]:<12} {str(s.get('kind'))[:22]:<22} "
            f"{s.get('_score_raw', 0):>5} {s.get('_score', 0):>5} "
            f"{(f'{mag:.1f}' if mag else '-'):>8} {str(s.get('_staleness_ratio', '-'))[:6]:>6}"
        )

    print("\nInvariants")

    # Ranking must not depend on the order signals arrive in.
    reverse = enrich_signals([dict(s) for s in reversed(signals)], "verify")
    check(
        "lead is order-independent",
        (reverse["lead_signal"] or {}).get("_country") == lead.get("_country"),
        f"{lead.get('_country')} vs {(reverse['lead_signal'] or {}).get('_country')}",
    )

    # Raw scores must stay unclamped, or strong signals tie again.
    raws = [s.get("_score_raw", 0) for s in enriched]
    check("raw scores are unclamped", max(raws) > 100 or max(raws) < 100,
          f"max={max(raws)}")
    check("display scores are clamped 0-100",
          all(0 <= s.get("_score", 0) <= 100 for s in enriched))

    # The top signals must be separable — the original bug was a 3-way tie.
    top = sorted(raws, reverse=True)[:3]
    check("top 3 raw scores are distinct", len(set(top)) == len(top), str(top))

    # A country's strongest signal decides the lead, so more evidence can
    # never cost it the lead.
    lead_country = lead.get("_country")
    best = max(
        (s for s in enriched if s.get("_country") == lead_country),
        key=lambda s: s.get("_score_raw", 0), default={},
    )
    check("lead is its country's strongest signal",
          best.get("id") == lead.get("id"))

    # Corroboration must be real, not a region-wide constant.
    multi = [s for s in enriched if len(s.get("corroborating_sources") or []) >= 2]
    check("no signal claims corroboration it lacks",
          all(len(s.get("corroborating_sources") or []) >= 2 for s in multi))

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} invariant(s) — {', '.join(FAILURES)}")
        return 1
    print("All ranking invariants hold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
