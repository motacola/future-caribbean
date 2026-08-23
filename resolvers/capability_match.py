#!/usr/bin/env python3
"""Match detected Caribbean procurement tenders to cited regional
capability-registry entries.

The claim this supports (handover §7 item 3):

    We detected this tender, classified its required capability, and a
    Caribbean country/bloc registry entry claims that capability and names
    the evidence supporting the claim.

It reuses two pieces of existing deterministic infrastructure rather
than inventing anything:

- ``coordination.engine.classify_tender`` — ordered keyword rules that map
  a tender's title/category/agency to a ``sector`` and a list of
  ``required_capabilities``.
- ``config/regional_capabilities.json`` — the pilot capability registry:
  per-country ``capabilities`` (with a ``strength``) and the ``evidence``
  (source, url, grade, supports[]) behind each capability claim.

Nothing here fetches or infers. A tender only matches a country if the
registry already asserts that country has the required capability, and the
match carries the registry's source, URL, and grade so it can be shown
honestly. This is country/bloc screening evidence, not audited supplier
capacity. A capability with no registry entry is reported as ``unmatched``.

Evidence grades (from the registry, propagated verbatim):
  primary      — primary-source documented
  corroborated — independently corroborated
  claimed      — publicly claimed (pilot, not audited supplier capacity)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Ensure the repository root is importable before the engine import below,
# so the module works both when imported (package context) and when run
# directly as `python3 resolvers/capability_match.py` (where sys.path[0] is
# the resolvers/ dir, not the repo root).
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coordination.engine import classify_tender

CAPABILITY_REGISTRY = ROOT / "config" / "regional_capabilities.json"


# ── registry loading ────────────────────────────────────────────────────

def load_registry(path: Path = CAPABILITY_REGISTRY) -> dict[str, Any]:
    """Load the registry fail-fast: a missing/invalid registry must not
    silently publish an empty capability surface."""
    return json.loads(path.read_text(encoding="utf-8"))


def _registry_index(registry: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """capability id → cited country/bloc registry entries."""
    index: dict[str, list[dict[str, Any]]] = {}
    for country in registry.get("countries", []):
        name = country.get("country") or ""
        for cap in country.get("capabilities", []):
            cap_id = cap.get("id")
            if not cap_id:
                continue
            evidence = [
                {
                    "source": ev.get("source"),
                    "url": ev.get("url"),
                    "grade": ev.get("grade"),
                }
                for ev in country.get("evidence", [])
                if cap_id in (ev.get("supports") or [])
            ]
            index.setdefault(cap_id, []).append({
                "country": name,
                "strength": cap.get("strength"),
                "evidence": evidence,
                "evidence_grades": [ev.get("grade") for ev in evidence],
            })
    return index


# ── matching ────────────────────────────────────────────────────────────

def best_grade(grades: list[str | None]) -> str | None:
    """Rank the registry's own evidence grades for an honest label."""
    order = ["primary", "corroborated", "claimed"]
    for g in order:
        if g in grades:
            return g
    return next((g for g in grades if g), None)


def _grade_rank(grades: list[str | None]) -> int:
    return {"primary": 0, "corroborated": 1, "claimed": 2}.get(
        best_grade(grades) or "", 3
    )


def match_tender(
    entry: dict[str, Any],
    index: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Classify one canonical tender and resolve its required capabilities
    against the registry. Returns the structured match record."""
    item = {
        "title": entry.get("title") or "",
        "category": entry.get("sector") or entry.get("method") or "",
        "agency": entry.get("buyer") or "",
    }
    classification = classify_tender(item)

    sector = classification.get("sector")
    required = classification.get("required_capabilities") or []
    matched_caps: list[dict[str, Any]] = []

    for cap in required:
        holders = index.get(cap) or []
        if not holders:
            matched_caps.append({
                "capability": cap,
                "matched": False,
                "holders": [],
            })
            continue
        holders_sorted = sorted(
            holders,
            key=lambda h: (_grade_rank(h["evidence_grades"]), -(h["strength"] or 0), h["country"]),
        )
        matched_caps.append({
            "capability": cap,
            "matched": True,
            "holders": holders_sorted,
        })

    classified = classification.get("classification") == "deterministic_keyword"
    any_match = any(c["matched"] for c in matched_caps)

    return {
        "tender_id": entry.get("tender_id"),
        "country": entry.get("country"),
        "title": entry.get("title"),
        "buyer": entry.get("buyer"),
        "lifecycle_state": entry.get("lifecycle_state"),
        "sector": sector,
        "classification": classification.get("classification"),
        "matched_keywords": classification.get("matched_keywords", []),
        "required_capabilities": required,
        "capability_matches": matched_caps,
        "has_capability_match": bool(any_match) and classified,
    }


def match_corpus(
    corpus: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fold the entire canonical corpus into capability matches."""
    registry = registry if registry is not None else load_registry()
    index = _registry_index(registry)
    entries = list(corpus.get("tenders", {}).values())
    matches = [match_tender(e, index) for e in entries]

    matched = [m for m in matches if m["has_capability_match"]]
    by_capability: dict[str, int] = {}
    by_country: dict[str, int] = {}
    for m in matched:
        for cap in m["capability_matches"]:
            if not cap["matched"]:
                continue
            by_capability[cap["capability"]] = by_capability.get(cap["capability"], 0) + 1
            for h in cap["holders"]:
                by_country[h["country"]] = by_country.get(h["country"], 0) + 1

    return {
        "schema_version": 1,
        "registry_status": registry.get("status"),
        "total_tenders": len(entries),
        "classified_tenders": sum(1 for m in matches if m["classification"] == "deterministic_keyword"),
        "tenders_with_capability_match": len(matched),
        "by_capability": dict(sorted(by_capability.items(), key=lambda kv: -kv[1])),
        "by_country": dict(sorted(by_country.items(), key=lambda kv: -kv[1])),
        "count_semantics": {
            "by_capability": "classified tender-capability links",
            "by_country": "classified tender-capability-country links; one tender can count more than once",
        },
        "matches": sorted(
            matched,
            key=lambda m: (m["country"] or "", m["title"] or "", m["tender_id"] or ""),
        ),
    }


def main() -> int:
    from resolvers import procurement as proc

    corpus = proc.load_corpus()
    if not corpus.get("tenders"):
        print("capability_match: no canonical tender corpus built yet")
        return 0
    result = match_corpus(corpus)
    out = ROOT / "outbox" / "capability_matches.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"capability matches -> {out.relative_to(ROOT)}")
    print(f"  {result['classified_tenders']} classified · "
          f"{result['tenders_with_capability_match']} with a registry capability match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
