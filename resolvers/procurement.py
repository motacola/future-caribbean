#!/usr/bin/env python3
"""Procurement Outcome Resolver — deterministic tender lifecycle tracking.

The claim this exists to earn:

    Signal Fabric detected this Caribbean procurement opportunity before
    close and subsequently recorded the award, supplier, value, and
    outcome.

`data/tenders/latest.json` is a live snapshot: it holds whatever the
portals showed on the last poll and nothing about what happened next.
This module accumulates those snapshots into a canonical, non-destructive
corpus keyed by a deterministic tender identity, links amendments and
closing-date changes to the original tender, and records award or
cancellation notices as resolutions of the tender that was detected —
not as unrelated new opportunities.

Contracts (CLAUDE_HANDOVER_2026-08-15 §6), enforced here and in tests:

1. Amendments and awards attach to the original tender.
2. A missing award stays `unresolved`. Never infer a winner.
3. The source that generated a claim cannot independently resolve it.
4. Close and award horizons are weeks/months, not the press horizon.
5. Deterministic identity and matching precede any model judgment.
6. The corpus is non-destructive; raw source receipts are preserved.

Supplier and award value are recorded only when a source states them.
The Jamaica GOJEP award listing publishes neither, so those fields stay
null on GOJEP-resolved tenders rather than being guessed from the title.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "procurement" / "canonical.json"

SCHEMA_VERSION = 1

# Lifecycle: detected → open → amended → closed → awarded | cancelled | unresolved
STATE_DETECTED = "detected"
STATE_OPEN = "open"
STATE_AMENDED = "amended"
STATE_CLOSED = "closed"
STATE_AWARDED = "awarded"
STATE_CANCELLED = "cancelled"
STATE_UNRESOLVED = "unresolved"

TERMINAL_STATES = {STATE_AWARDED, STATE_CANCELLED}

# How long a closed tender waits for an award notice before it is reported
# unresolved. Procurement horizons are weeks to months (contract 4), so this
# is deliberately far longer than any press-pickup window.
UNRESOLVED_AFTER_DAYS = 180

# Portal status strings → lifecycle state. Anything unrecognized is treated
# as a detection only; the resolver does not guess what a new status means.
STATUS_MAP = {
    "bid submission": STATE_OPEN,
    "bid opening": STATE_CLOSED,
    "evaluation": STATE_CLOSED,
    "awarded": STATE_AWARDED,
    "award": STATE_AWARDED,
    "cancelled": STATE_CANCELLED,
    "canceled": STATE_CANCELLED,
    "annulled": STATE_CANCELLED,
}

# Notice feeds that publish outcomes rather than opportunities. A record from
# one of these resolves a tender; it never creates a new "opportunity".
_RESOLUTION_HINTS = ("award", "cancel", "annul")

_TITLE_NOISE = re.compile(
    r"^(request for quotation|request for proposal|invitation to bid|rfq|rfp|itb)\b[\s–—:-]*",
    re.I,
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


# ── identity ────────────────────────────────────────────────────────────

def normalize_title(title: str) -> str:
    """Reduce a portal title to a stable matching key.

    Conservative on purpose: an award notice and its opened-bid record must
    collapse to the same key, but two genuinely different tenders from the
    same buyer must not. Only casing, punctuation, whitespace and a leading
    procurement-method prefix are removed — no stemming, no truncation, no
    fuzzy distance.
    """
    text = _TITLE_NOISE.sub("", (title or "").strip())
    return _NON_ALNUM.sub(" ", text.lower()).strip()


def normalize_buyer(agency: str) -> str:
    return _NON_ALNUM.sub(" ", (agency or "").lower()).strip()


def canonical_id(country: str, agency: str, title: str) -> str:
    """Deterministic tender identity.

    Keyed on country, buyer and normalized title rather than the portal's
    reference id: GOJEP award notices carry no reference id, so a
    ref-keyed identity could never link an award back to the opportunity
    it resolves.
    """
    basis = f"{(country or '').strip().lower()}|{normalize_buyer(agency)}|{normalize_title(title)}"
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]
    prefix = _NON_ALNUM.sub("-", (country or "unknown").lower()).strip("-") or "unknown"
    return f"{prefix}-{digest}"


def is_resolution_notice(record: dict[str, Any]) -> bool:
    source = (record.get("source") or "").lower()
    status = (record.get("status") or "").lower()
    return any(h in source for h in _RESOLUTION_HINTS) or status in {"awarded", "cancelled", "canceled"}


def lifecycle_from_status(status: str) -> str | None:
    return STATUS_MAP.get((status or "").strip().lower())


# ── independence ────────────────────────────────────────────────────────

# Which institution stands behind each feed. Independence is a claim about
# publishers, not about feed names, so this mapping is explicit: inferring
# it from the source string classified "IDB Procurement Notices" and "IDB
# Contract Award Notifications" as two publishers and manufactured 68
# independent resolutions out of one institution resolving itself.
PUBLISHERS = {
    "Jamaica GOJEP (opened bids)": "jamaica-gojep",
    "Jamaica GOJEP (contract award)": "jamaica-gojep",
    "Jamaica GOJEP (cancellation)": "jamaica-gojep",
    "Guyana eProcure (NPTA)": "guyana-eprocure",
    "IDB Procurement Notices": "idb",
    "IDB Contract Award Notifications": "idb",
}


def _publisher(source: str) -> str:
    """The institution behind a feed.

    Registered feeds map to their publisher. An unregistered source falls
    back to stripping the parenthetical feed qualifier — a guess, so a new
    feed should be added to PUBLISHERS rather than relying on it.
    """
    if source in PUBLISHERS:
        return PUBLISHERS[source]
    return re.sub(r"\s*\(.*?\)\s*", " ", source or "").strip().lower()


def classify_independence(generating_sources: Iterable[str], resolving_source: str) -> str:
    """How much independence a resolution actually has.

    Contract 3: a source cannot validate its own prediction. The honest
    middle case matters here — GOJEP's award listing is a different notice
    feed from its opened-bid listing, but the same portal publishes both,
    so it is reported as `same_publisher`, never as independent
    corroboration.
    """
    gen = list(generating_sources or [])
    if not gen:
        # An award notice for a tender we never detected as an opportunity.
        # Absence of a generating source is not independence — there is no
        # prediction here for the award to corroborate.
        return "no_prior_detection"
    if resolving_source in gen:
        return "same_source"
    if _publisher(resolving_source) in {_publisher(s) for s in gen}:
        return "same_publisher"
    return "independent"


# ── corpus ──────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def _days_between(start: str | None, end: str | None) -> int | None:
    a, b = _as_date(start), _as_date(end)
    if a is None or b is None:
        return None
    return (b - a).days


def _new_record(rec: dict[str, Any], tender_id: str, observed_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tender_id": tender_id,
        "country": rec.get("country") or "",
        "buyer": rec.get("agency") or "",
        "title": (rec.get("title") or "").strip(),
        "sector": rec.get("category") or "",
        "method": rec.get("method") or "",
        "source_ref_ids": [],
        "generating_sources": [],
        "urls": [],
        "published": rec.get("published"),
        "original_closing_date": None,
        "current_closing_date": None,
        "amendments": [],
        "notices": [],
        "first_detected_at": observed_at,
        "lifecycle_state": STATE_DETECTED,
        "resolution": None,
        "detected_before_close": None,
        "lead_time_days": None,
        "award_lead_time_days": None,
        "last_seen_at": observed_at,
    }


def _record_notice(entry: dict[str, Any], rec: dict[str, Any], observed_at: str) -> None:
    """Append a source receipt. Notices are the raw evidence trail: one per
    distinct (source, status, closing date, observation day)."""
    notice = {
        "source": rec.get("source") or "",
        "source_ref_id": rec.get("id") or "",
        "url": rec.get("url") or "",
        "status": rec.get("status") or "",
        "closing_date": rec.get("closing_date"),
        "published": rec.get("published"),
        "observed_at": observed_at,
    }
    fingerprint = (notice["source"], notice["status"], notice["closing_date"], observed_at[:10])
    for existing in entry["notices"]:
        if (existing["source"], existing["status"], existing["closing_date"], existing["observed_at"][:10]) == fingerprint:
            return
    entry["notices"].append(notice)


def _apply_closing_date(entry: dict[str, Any], rec: dict[str, Any], observed_at: str) -> None:
    """Closing-date changes are amendments of the same tender, never a new
    opportunity (contract 1)."""
    closing = rec.get("closing_date")
    if not closing:
        return
    if entry["original_closing_date"] is None:
        entry["original_closing_date"] = closing
        entry["current_closing_date"] = closing
        return
    if closing != entry["current_closing_date"]:
        entry["amendments"].append({
            "type": "closing_date_change",
            "from": entry["current_closing_date"],
            "to": closing,
            "observed_at": observed_at,
            "source": rec.get("source") or "",
            "url": rec.get("url") or "",
        })
        entry["current_closing_date"] = closing


def _apply_resolution(entry: dict[str, Any], rec: dict[str, Any], observed_at: str) -> None:
    """Attach an award or cancellation to the tender it resolves.

    Supplier and value are copied only from explicit source fields. The
    GOJEP award listing carries neither, so they stay null — an unnamed
    winner is recorded as unnamed, never inferred (contract 2).
    """
    state = lifecycle_from_status(rec.get("status") or "") or STATE_AWARDED
    if state not in TERMINAL_STATES:
        state = STATE_AWARDED
    source = rec.get("source") or ""
    resolution = {
        "state": state,
        "resolved_at": rec.get("published") or observed_at[:10],
        "resolution_source": source,
        "resolution_url": rec.get("url") or "",
        "independence": classify_independence(entry["generating_sources"], source),
        "resolves_prior_detection": bool(entry["generating_sources"]),
        "supplier": rec.get("supplier"),
        "award_value": rec.get("award_value"),
        "award_currency": rec.get("award_currency"),
        "observed_at": observed_at,
    }
    existing = entry.get("resolution")
    if existing and existing.get("state") in TERMINAL_STATES:
        # First terminal outcome wins; later sightings of the same notice
        # must not rewrite history.
        return
    entry["resolution"] = resolution
    entry["lifecycle_state"] = state


def _derive_state(entry: dict[str, Any], today: date | None = None) -> None:
    """Lifecycle state from evidence, evaluated after every observation."""
    if entry.get("resolution") and entry["resolution"]["state"] in TERMINAL_STATES:
        entry["lifecycle_state"] = entry["resolution"]["state"]
        return

    today = today or datetime.now(timezone.utc).date()
    statuses = [lifecycle_from_status(n["status"]) for n in entry["notices"]]
    closing = _as_date(entry.get("current_closing_date"))

    if STATE_CLOSED in statuses or (closing is not None and closing < today):
        state = STATE_CLOSED
    elif STATE_OPEN in statuses:
        state = STATE_OPEN
    else:
        state = STATE_DETECTED

    if state == STATE_OPEN and entry["amendments"]:
        state = STATE_AMENDED

    if state == STATE_CLOSED:
        closed_on = closing or _as_date(entry["last_seen_at"])
        if closed_on and (today - closed_on).days > UNRESOLVED_AFTER_DAYS:
            state = STATE_UNRESOLVED

    entry["lifecycle_state"] = state


def _derive_timings(entry: dict[str, Any]) -> None:
    """Detection lead time — the number the product claim rests on."""
    detected = entry["first_detected_at"]
    closing = entry.get("current_closing_date")
    entry["lead_time_days"] = _days_between(detected, closing)
    if entry["lead_time_days"] is not None:
        entry["detected_before_close"] = entry["lead_time_days"] > 0
    resolution = entry.get("resolution")
    if resolution:
        entry["award_lead_time_days"] = _days_between(detected, resolution.get("resolved_at"))


def _title_index(tenders: dict[str, Any]) -> dict[tuple[str, str], list[str]]:
    index: dict[tuple[str, str], list[str]] = {}
    for tid, entry in tenders.items():
        index.setdefault((entry["country"].lower(), normalize_title(entry["title"])), []).append(tid)
    return index


def resolve_identity(rec: dict[str, Any], tenders: dict[str, Any],
                     index: dict[tuple[str, str], list[str]]) -> str:
    """Which canonical tender a record belongs to.

    The strict identity is country + buyer + title. Multilateral notice
    feeds publish no executing agency, so a strict key would file the IDB
    notice and the national portal's record for the same tender as two
    unrelated opportunities — and an award from one publisher could never
    resolve a detection from the other.

    So when one side carries no buyer, a record may join an existing
    tender with the same country and title. Only an unambiguous match is
    accepted: if two buyers are running tenders with the same title, the
    records stay separate rather than being merged on a guess.
    """
    strict = canonical_id(rec.get("country") or "", rec.get("agency") or "", rec.get("title") or "")
    if strict in tenders:
        return strict

    key = ((rec.get("country") or "").lower(), normalize_title(rec.get("title") or ""))
    incoming_buyer = normalize_buyer(rec.get("agency") or "")
    candidates = [
        tid for tid in index.get(key, [])
        if not incoming_buyer or not normalize_buyer(tenders[tid]["buyer"])
    ]
    if len(candidates) == 1:
        tid = candidates[0]
        # A record that names the buyer fills in one that did not.
        if incoming_buyer and not tenders[tid]["buyer"]:
            tenders[tid]["buyer"] = rec.get("agency") or ""
        return tid
    return strict


def observe(
    records: Iterable[dict[str, Any]],
    corpus: dict[str, Any] | None = None,
    observed_at: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Fold a batch of portal records into the canonical corpus.

    Non-destructive: existing tenders accumulate notices, amendments and
    resolutions. Deterministic: the same inputs in any order produce the
    same corpus, so replaying the raw snapshot archive reproduces history
    exactly.
    """
    observed_at = observed_at or _now()
    corpus = corpus or {"schema_version": SCHEMA_VERSION, "tenders": {}}
    tenders: dict[str, Any] = corpus.setdefault("tenders", {})

    # Opportunity notices before resolution notices, so an award always has
    # a detection to attach to when both arrive in one batch.
    batch = sorted(
        (r for r in records if r.get("title")),
        key=lambda r: (is_resolution_notice(r), r.get("id") or "", r.get("source") or ""),
    )

    index = _title_index(tenders)

    for rec in batch:
        tender_id = resolve_identity(rec, tenders, index)
        entry = tenders.get(tender_id)
        if entry is None:
            entry = _new_record(rec, tender_id, observed_at)
            tenders[tender_id] = entry
            index.setdefault(
                (entry["country"].lower(), normalize_title(entry["title"])), []
            ).append(tender_id)

        entry["last_seen_at"] = observed_at
        ref = rec.get("id") or ""
        if ref and ref not in entry["source_ref_ids"]:
            entry["source_ref_ids"].append(ref)
        url = rec.get("url") or ""
        if url and url not in entry["urls"]:
            entry["urls"].append(url)
        if rec.get("published") and not entry.get("published"):
            entry["published"] = rec["published"]

        _record_notice(entry, rec, observed_at)

        if is_resolution_notice(rec):
            _apply_resolution(entry, rec, observed_at)
        else:
            source = rec.get("source") or ""
            if source and source not in entry["generating_sources"]:
                entry["generating_sources"].append(source)
            _apply_closing_date(entry, rec, observed_at)

        _derive_state(entry, today=today)
        _derive_timings(entry)

    corpus["schema_version"] = SCHEMA_VERSION
    corpus["updated_at"] = observed_at
    return corpus


def refresh(corpus: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    """Re-derive states without new observations, so a closed tender ages
    into `unresolved` on its own rather than waiting for a poll."""
    for entry in corpus.get("tenders", {}).values():
        _derive_state(entry, today=today)
        _derive_timings(entry)
    return corpus


# ── persistence ─────────────────────────────────────────────────────────

def load_corpus(path: Path = CORPUS) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"schema_version": SCHEMA_VERSION, "tenders": {}}


def save_corpus(corpus: dict[str, Any], path: Path = CORPUS) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = {
        "schema_version": corpus.get("schema_version", SCHEMA_VERSION),
        "updated_at": corpus.get("updated_at"),
        "tenders": {k: corpus["tenders"][k] for k in sorted(corpus.get("tenders", {}))},
    }
    path.write_text(json.dumps(ordered, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_live_records(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or ROOT / "data" / "tenders" / "latest.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    return payload.get("items", []) or []


def main() -> int:
    records = load_live_records()
    if not records:
        print("procurement: no tender records to observe (data/tenders/latest.json empty or absent)")
        return 0
    corpus = observe(records, load_corpus())
    refresh(corpus)
    dest = save_corpus(corpus)

    tenders = corpus["tenders"].values()
    states: dict[str, int] = {}
    for t in tenders:
        states[t["lifecycle_state"]] = states.get(t["lifecycle_state"], 0) + 1
    print(f"procurement: {len(corpus['tenders'])} canonical tenders -> {dest.relative_to(ROOT)}")
    print("  " + ", ".join(f"{k}={v}" for k, v in sorted(states.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
