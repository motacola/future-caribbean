#!/usr/bin/env python3
"""Publish the procurement outcome view from the canonical corpus.

The corpus (data/procurement/canonical.json) is the accumulating record.
This is the read-only projection the site and API serve: one entry per
canonical tender with its detection date, closing date, amendments,
outcome and the source receipts behind each, plus a summary that states
what the evidence does and does not establish.

Nothing here infers. If a portal never named the supplier, the supplier
is null and the summary says how many outcomes lack one, rather than
publishing a number that implies we know.
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
import sys  # noqa: E402
sys.path.insert(0, str(ROOT))

from resolvers import procurement as proc  # noqa: E402

OUT = ROOT / "outbox" / "procurement_outcomes.json"
PUBLIC = ROOT / "public" / "procurement_outcomes.json"


def public_view(entry: dict[str, Any]) -> dict[str, Any]:
    resolution = entry.get("resolution")
    return {
        "tender_id": entry["tender_id"],
        "country": entry["country"],
        "buyer": entry["buyer"],
        "title": entry["title"],
        "sector": entry["sector"],
        "method": entry["method"],
        "source_ref_ids": entry["source_ref_ids"],
        "generating_sources": entry["generating_sources"],
        "urls": entry["urls"],
        "first_detected_at": entry["first_detected_at"],
        "original_closing_date": entry["original_closing_date"],
        "current_closing_date": entry["current_closing_date"],
        "amendments": entry["amendments"],
        "lifecycle_state": entry["lifecycle_state"],
        "detected_before_close": entry["detected_before_close"],
        "lead_time_days": entry["lead_time_days"],
        "award_lead_time_days": entry["award_lead_time_days"],
        "notice_count": len(entry["notices"]),
        "resolution": resolution,
        "last_seen_at": entry["last_seen_at"],
    }


def summarize(entries: list[dict[str, Any]]) -> dict[str, Any]:
    by_state: dict[str, int] = {}
    for e in entries:
        by_state[e["lifecycle_state"]] = by_state.get(e["lifecycle_state"], 0) + 1

    resolved = [e for e in entries if e.get("resolution")]
    corroborating = [e for e in resolved if e["resolution"].get("resolves_prior_detection")]
    independence: dict[str, int] = {}
    for e in resolved:
        k = e["resolution"]["independence"]
        independence[k] = independence.get(k, 0) + 1

    leads = [e["lead_time_days"] for e in entries if (e.get("lead_time_days") or 0) > 0]
    named_suppliers = [e for e in resolved if e["resolution"].get("supplier")]

    return {
        "tenders": len(entries),
        "by_state": dict(sorted(by_state.items())),
        "countries": sorted({e["country"] for e in entries if e["country"]}),
        "resolved_outcomes": len(resolved),
        "outcomes_resolving_a_prior_detection": len(corroborating),
        "independently_resolved": independence.get("independent", 0),
        "resolution_independence": dict(sorted(independence.items())),
        "detected_before_close": len(leads),
        "median_lead_days": int(statistics.median(leads)) if leads else None,
        "max_lead_days": max(leads) if leads else None,
        "amendments_linked": sum(len(e["amendments"]) for e in entries),
        "outcomes_with_named_supplier": len(named_suppliers),
        "outcomes_without_named_supplier": len(resolved) - len(named_suppliers),
    }


def provenance(entries: list[dict[str, Any]]) -> dict[str, Any]:
    sources = sorted({s for e in entries for s in e["generating_sources"]})
    resolvers = sorted({
        e["resolution"]["resolution_source"] for e in entries if e.get("resolution")
    })
    return {
        "generating_sources": sources,
        "resolution_sources": resolvers,
        "notes": [
            "Supplier and award value are published only when a source states them. "
            "The Jamaica GOJEP award listing publishes neither.",
            "`independence` reports how much distance a resolution has from the source "
            "that generated the claim: independent, same_publisher (a different notice "
            "feed from the same portal), same_source, or no_prior_detection.",
            "Jamaica GOJEP's opened-bid feed lists tenders whose bids have already been "
            "opened, so detections from it are at or after close, not before it.",
        ],
    }


def build(corpus: dict[str, Any] | None = None) -> dict[str, Any]:
    corpus = corpus if corpus is not None else proc.load_corpus()
    entries = [public_view(e) for e in corpus.get("tenders", {}).values()]
    entries.sort(key=lambda e: (e["first_detected_at"], e["tender_id"]), reverse=True)
    return {
        "schema_version": corpus.get("schema_version", proc.SCHEMA_VERSION),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus_updated_at": corpus.get("updated_at"),
        "summary": summarize(entries),
        "provenance": provenance(entries),
        "tenders": entries,
    }


def main() -> int:
    payload = build()
    body = json.dumps(payload, indent=1, ensure_ascii=False) + "\n"
    for dest in (OUT, PUBLIC):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
    s = payload["summary"]
    print(f"procurement outcomes -> {OUT.relative_to(ROOT)}, {PUBLIC.relative_to(ROOT)}")
    print(f"  {s['tenders']} tenders · {s['resolved_outcomes']} outcomes "
          f"({s['outcomes_resolving_a_prior_detection']} resolving a prior detection, "
          f"{s['independently_resolved']} independently)")
    print(f"  {s['detected_before_close']} detected before close · "
          f"median lead {s['median_lead_days']}d · max {s['max_lead_days']}d")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
