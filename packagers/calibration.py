#!/usr/bin/env python3
"""Calibration ledger: turn asserted confidence into measured reliability.

The desk publishes a confidence score with every signal. Until now that number
was a weighted sum of hand-set constants — it had no relationship to how often
the desk turned out to be right, so "100/100" meant "our formula maxed out",
not "we are certain".

This module closes that loop. Every cycle it:

  1. RECORDS what each signal claimed, keyed by the underlying fact.
  2. RESOLVES older claims by checking what later cycles found out about the
     same fact.
  3. REPORTS reliability per score band, so the page can say "signals we
     scored 70-84 were confirmed 61% of the time" instead of "84/100".

What counts as confirmation
---------------------------
We deliberately do NOT claim to measure whether an investment thesis paid off;
nobody observes that within a news cycle, and pretending otherwise would be
the same overclaiming this codebase already had. What is observable is whether
a signal we published on thin evidence *held up*: did an independent source
corroborate the same fact within the resolution window, and did the fact
persist rather than vanish or reverse?

That is a real, falsifiable prediction the desk makes every cycle:
"this is worth your attention" implies "this will still look real next week".

Reliability computed this way cannot be cloned from the code — it only exists
once a deployment has accumulated cycles.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LEDGER_FILE = ROOT / "data" / "calibration" / "ledger.json"
REPORT_FILE = ROOT / "outbox" / "calibration.json"

# A claim is left open this many cycles before we judge it. Long enough for a
# second source to appear, short enough to stay honest about recency.
RESOLUTION_WINDOW_CYCLES = 3

# Score bands reported to readers. Upper bound is exclusive.
BANDS: tuple[tuple[str, int, int], ...] = (
    ("85-100", 85, 1000),
    ("70-84", 70, 85),
    ("55-69", 55, 70),
    ("0-54", 0, 55),
)

# A band needs this many resolved claims before its rate is worth printing.
MIN_SAMPLE = 5

# ── Public pre-commitment ──────────────────────────────────
# Accuracy targets published BEFORE the claims resolve. A track record that
# only appears once it looks good is worthless; committing to numbers we might
# miss is the point. These are data, not code — moving a gate is a visible
# diff, and `committed_at` is the date the promise was made.
COMMITMENT_MADE_AT = "2026-08-15"
COMMITMENTS: tuple[dict[str, Any], ...] = (
    {"milestone": "Day 30", "day": 30, "min_resolved": 20, "max_brier": None},
    {"milestone": "Day 60", "day": 60, "min_resolved": 80, "max_brier": 0.22},
    {"milestone": "Day 90", "day": 90, "min_resolved": 150, "max_brier": 0.20},
    {"milestone": "Year 1", "day": 365, "min_resolved": 200, "max_brier": 0.18},
)


# ── Tamper-evidence ────────────────────────────────────────
# Each claim carries the hash of the one before it. A track record is only
# worth anything if it cannot be quietly rewritten after the fact — this makes
# any edit to a historical claim detectable without a chain dependency.
# Only the fields fixed at claim time are hashed; resolution fields are set
# later and are deliberately excluded.

CHAIN_FIELDS = (
    "cycle_id", "fact_key", "signal_id", "kind", "country",
    "score", "band", "corroborating_at_claim", "forecast_probability", "recorded_at",
)
GENESIS_HASH = "0" * 64


def claim_digest(claim: dict[str, Any], previous_hash: str) -> str:
    payload = json.dumps(
        {k: claim.get(k) for k in CHAIN_FIELDS},
        sort_keys=True, separators=(",", ":"), default=str,
    )
    return hashlib.sha256((previous_hash + payload).encode("utf-8")).hexdigest()


def verify_chain(ledger: dict[str, Any]) -> tuple[bool, int | None]:
    """(intact, index_of_first_break). A break means a claim was edited."""
    previous = GENESIS_HASH
    for i, claim in enumerate(ledger.get("claims", [])):
        if claim.get("prev_hash") != previous:
            return (False, i)
        if claim.get("hash") != claim_digest(claim, previous):
            return (False, i)
        previous = claim["hash"]
    return (True, None)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_ledger() -> dict[str, Any]:
    if LEDGER_FILE.exists():
        try:
            data = json.loads(LEDGER_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("claims", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"claims": [], "created_at": _now()}


def save_ledger(ledger: dict[str, Any]) -> None:
    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = _now()
    LEDGER_FILE.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


def band_for(score: int) -> str:
    for label, low, high in BANDS:
        if low <= score < high:
            return label
    return BANDS[-1][0]


# ── Forecast probability ───────────────────────────────────
# Brier and log-loss need a probability, but the score is not one — that is
# the whole problem calibration exists to solve. So each claim records the
# best probability available AT CLAIM TIME, and says which it used:
#
#   "calibrated" — the band's own historical confirmation rate. Out-of-sample:
#                  it uses only claims already resolved when this one was made.
#   "naive"      — score/100, the null model. This is the implicit claim the
#                  product makes by printing "84/100", so measuring Brier
#                  against it shows exactly how wrong that implication is.
#
# Improvement of "calibrated" over "naive" is the value the ledger adds, and
# it is measurable rather than asserted.

PROBABILITY_FLOOR = 0.05
PROBABILITY_CEILING = 0.95


def _clamp_probability(p: float) -> float:
    return max(PROBABILITY_FLOOR, min(PROBABILITY_CEILING, p))


def forecast_probability(score: int, ledger: dict[str, Any]) -> tuple[float, str]:
    """Best probability for a score, using only already-resolved claims."""
    label = band_for(score)
    outcomes = [
        c["outcome"] for c in ledger.get("claims", [])
        if c.get("outcome") is not None and c.get("band") == label
    ]
    if len(outcomes) >= MIN_SAMPLE:
        rate = sum(1 for o in outcomes if o == "confirmed") / len(outcomes)
        return (_clamp_probability(rate), "calibrated")
    return (_clamp_probability(score / 100), "naive")


def brier_score(pairs: list[tuple[float, int]]) -> float | None:
    """Mean squared error of probabilistic forecasts. Lower is better."""
    if not pairs:
        return None
    return round(sum((p - y) ** 2 for p, y in pairs) / len(pairs), 4)


def log_loss(pairs: list[tuple[float, int]]) -> float | None:
    if not pairs:
        return None
    total = sum(
        -(y * math.log(_clamp_probability(p)) + (1 - y) * math.log(1 - _clamp_probability(p)))
        for p, y in pairs
    )
    return round(total / len(pairs), 4)


def _fact_of(signal: dict[str, Any]) -> str:
    return signal.get("fact_key") or f"id:{signal.get('id', '')}"


def score_published_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply the desk's scoring path without reading or rewriting editorial state.

    Calibration must record the score readers actually saw. Calling only
    ``compute_signal_score`` misses both current feedback and the cross-signal
    FDI magnitude transfer that happens before publication.
    """
    from packagers.editorial_enrichment import (
        _transfer_fdi_magnitudes,
        compute_signal_score,
        display_score,
        extract_country,
        feedback_boost_for,
        load_feedback_boosts,
    )

    load_feedback_boosts()
    scored: list[dict[str, Any]] = []
    for signal in signals:
        item = dict(signal)
        item["_country"] = extract_country(item)
        raw = compute_signal_score(item) + feedback_boost_for(item)
        item["_score_raw"] = raw
        item["_score"] = display_score(raw)
        scored.append(item)

    _transfer_fdi_magnitudes(scored)
    return scored


def record_cycle(signals: list[dict[str, Any]], cycle_id: str) -> dict[str, Any]:
    """Append this cycle's claims to the ledger (idempotent per cycle)."""
    ledger = load_ledger()
    existing = {(c["cycle_id"], c["fact_key"]) for c in ledger["claims"]}

    previous_hash = ledger["claims"][-1]["hash"] if ledger["claims"] else GENESIS_HASH

    # Several detectors can describe the same underlying observation. Collapse
    # those records before writing the ledger so one fact cannot become several
    # calibration outcomes merely because it was routed through several signal
    # kinds. Pick the strongest published score as the representative claim,
    # while retaining every cited source for later independence checks.
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for signal in signals:
        fact = _fact_of(signal)
        if (cycle_id, fact) not in existing:
            grouped[fact].append(signal)

    for fact in sorted(grouped):
        variants = grouped[fact]
        sig = max(
            variants,
            key=lambda item: (int(item.get("_score", 0)), str(item.get("id", ""))),
        )
        score = int(sig.get("_score", 0))
        probability, basis = forecast_probability(score, ledger)
        cited_sources = sorted({
            source
            for variant in variants
            for source in (
                *(variant.get("corroborating_sources") or []),
                *(variant.get("context_sources") or []),
                *(variant.get("sources") or []),
            )
        })
        corroborating_count = max(
            (
                len(variant.get("corroborating_sources") or variant.get("sources") or [])
                for variant in variants
            ),
            default=0,
        )
        claim = {
            "cycle_id": cycle_id,
            "fact_key": fact,
            "signal_id": sig.get("id", ""),
            "kind": sig.get("kind", ""),
            "country": sig.get("_country", "") or (sig.get("countries") or [""])[0],
            "score": score,
            "band": band_for(score),
            "corroborating_at_claim": corroborating_count,
            # Every source already attached to the signal — corroborating AND
            # context. A source we have already cited to the reader cannot
            # later count as independent confirmation of the same claim.
            "source_names": cited_sources,
            "recorded_at": _now(),
            "forecast_probability": probability,
            "prior_basis": basis,
            "outcome": None,          # "confirmed" | "faded" — set on resolution
            "resolved_by": None,      # which resolver decided, see RESOLVER_*
            "resolved_at": None,
        }
        claim["prev_hash"] = previous_hash
        claim["hash"] = claim_digest(claim, previous_hash)
        previous_hash = claim["hash"]
        ledger["claims"].append(claim)
    return ledger


# What an independent publisher would have to be writing about for a signal
# of this kind to count as externally corroborated.
KIND_TOPICS: dict[str, set[str]] = {
    "enhanced_investment": {"finance", "trade"},
    "investment_signal": {"finance", "trade"},
    "development_pipeline": {"procurement", "finance"},
    "food_security": {"trade"},
    "tourism_impact": {"tourism"},
    "economic_vulnerability": {"finance"},
    "supply_chain": {"trade", "procurement"},
}

# Resolver strength, strongest first. Recorded per claim so the report can
# separate "the outside world agreed" from "our own pipeline kept saying it".
RESOLVER_EXTERNAL = "external_publisher"
RESOLVER_INDICATOR = "indicator_revision"
RESOLVER_INTERNAL = "internal_persistence"
EXTERNAL_RESOLVERS = (RESOLVER_EXTERNAL, RESOLVER_INDICATOR)


def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


# Source name -> domain fragments that are the SAME organisation. Without
# this, "World Bank" does not match "worldbank.org" and an institution ends up
# corroborating its own signal.
SOURCE_DOMAIN_ALIASES: dict[str, tuple[str, ...]] = {
    "world bank": ("worldbank", "wb.org"),
    "idb": ("iadb", "iadb.org"),
    "caricom": ("caricom",),
    "cdb": ("caribank", "cdb.org"),
    "eccb": ("eccb-centralbank", "eccb"),
    "noaa": ("noaa",),
    "ndbc": ("ndbc",),
    "ccrif": ("ccrif",),
}


def _slug(text: str) -> str:
    return "".join(ch for ch in str(text).lower() if ch.isalnum())


def _is_own_source(domain: str, source_names: list[str]) -> bool:
    domain_slug = _slug(domain)
    for name in source_names:
        key = str(name).strip().lower()
        if _slug(key) and _slug(key) in domain_slug:
            return True
        for alias in SOURCE_DOMAIN_ALIASES.get(key, ()):
            if _slug(alias) in domain_slug:
                return True
    return False


def external_publishers_for(claim: dict[str, Any], news_items: list[dict[str, Any]]) -> list[str]:
    """Independent publishers that covered this claim's country and topic after
    we published it.

    Independence is by publisher domain, and we exclude the sources the signal
    itself was built from — a World Bank signal is not corroborated by the
    World Bank.
    """
    claimed_at = _parse_dt(claim.get("recorded_at"))
    if claimed_at is None:
        return []
    country = (claim.get("country") or "").lower()
    if not country:
        return []
    topics = KIND_TOPICS.get(claim.get("kind", ""), set())
    own = list(claim.get("source_names") or [])

    found: set[str] = set()
    for item in news_items:
        published = _parse_dt(item.get("published"))
        if published is None or published <= claimed_at:
            continue
        if not any(country == str(c).lower() for c in item.get("countries") or []):
            continue
        if topics and not (topics & {str(t).lower() for t in item.get("topics") or []}):
            continue
        domain = str(item.get("publisher_domain") or item.get("publisher_name") or "").lower()
        if not domain or _is_own_source(domain, own):
            continue
        found.add(domain)
    return sorted(found)


def indicator_verdict(claim: dict[str, Any], observations: list[dict[str, Any]]) -> str | None:
    """Did a NEWER release of the same indicator hold the claim up?

    fact_key is country|indicator|period, so a later observation for the same
    country and indicator is the real-world follow-up to what we published.
    """
    parts = str(claim.get("fact_key") or "").split("|")
    if len(parts) != 3 or not parts[2].isdigit():
        return None
    country, indicator, period = parts[0], parts[1], int(parts[2])
    for obs in observations or []:
        if str(obs.get("country_name")) != country or str(obs.get("indicator_code")) != indicator:
            continue
        year = obs.get("year")
        if not isinstance(year, int) or year <= period:
            continue
        # A newer release exists. It confirms the claim if the level did not
        # give back the move we reported.
        return "confirmed" if (obs.get("delta_pct") or 0) > -25 else "faded"
    return None


def resolve_claims(
    ledger: dict[str, Any],
    cycle_id: str,
    news_items: list[dict[str, Any]] | None = None,
    observations: list[dict[str, Any]] | None = None,
) -> int:
    """Judge claims old enough to have had a fair chance.

    Resolution prefers outside evidence, in this order:

      1. An independent publisher covered the same country and topic after we
         published (strongest — the world agreed, not just us).
      2. A newer release of the same indicator held the move up.
      3. Fall back to internal persistence: our own pipeline kept reporting the
         fact with at least as much corroboration. Recorded as the weakest
         verdict so the report can discount it.
    """
    claims = ledger["claims"]
    cycles = sorted({c["cycle_id"] for c in claims})
    if cycle_id not in cycles:
        cycles = sorted(cycles + [cycle_id])
    position = {cid: i for i, cid in enumerate(cycles)}
    current = position.get(cycle_id, len(cycles) - 1)

    # What each later cycle knew about each fact.
    seen_after: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for claim in claims:
        seen_after[claim["fact_key"]].append(
            (position.get(claim["cycle_id"], 0), claim["corroborating_at_claim"])
        )

    resolved = 0
    for claim in claims:
        if claim["outcome"] is not None:
            continue
        claimed_at = position.get(claim["cycle_id"], 0)
        if current - claimed_at < RESOLUTION_WINDOW_CYCLES:
            continue  # still inside its window — leave it open

        publishers = external_publishers_for(claim, news_items or [])
        if publishers:
            claim["outcome"] = "confirmed"
            claim["resolved_by"] = RESOLVER_EXTERNAL
            claim["external_publishers"] = publishers[:5]
        else:
            verdict = indicator_verdict(claim, observations or [])
            if verdict:
                claim["outcome"] = verdict
                claim["resolved_by"] = RESOLVER_INDICATOR
            else:
                later = [
                    corroboration for pos, corroboration in seen_after[claim["fact_key"]]
                    if pos > claimed_at
                ]
                held_up = any(c >= claim["corroborating_at_claim"] for c in later)
                claim["outcome"] = "confirmed" if held_up else "faded"
                claim["resolved_by"] = RESOLVER_INTERNAL
        claim["resolved_at"] = _now()
        resolved += 1
    return resolved


def reliability(ledger: dict[str, Any]) -> dict[str, Any]:
    """Confirmation rate per score band, over resolved claims only."""
    buckets: dict[str, list[str]] = defaultdict(list)
    for claim in ledger["claims"]:
        if claim["outcome"] is not None:
            buckets[claim["band"]].append(claim["outcome"])

    # Track how each verdict was reached: a rate built on outside evidence is
    # worth more than one built on our own pipeline agreeing with itself.
    by_resolver: dict[str, int] = defaultdict(int)
    externally_resolved = 0
    for claim in ledger["claims"]:
        if claim.get("outcome") is None:
            continue
        resolver = claim.get("resolved_by") or RESOLVER_INTERNAL
        by_resolver[resolver] += 1
        if resolver in EXTERNAL_RESOLVERS:
            externally_resolved += 1

    bands_out = []
    for label, _, _ in BANDS:
        outcomes = buckets.get(label, [])
        confirmed = sum(1 for o in outcomes if o == "confirmed")
        n = len(outcomes)
        bands_out.append({
            "band": label,
            "resolved": n,
            "confirmed": confirmed,
            # None, not 0, when we have not earned the right to a number.
            "confirmation_rate": round(confirmed / n, 3) if n >= MIN_SAMPLE else None,
            "sufficient_sample": n >= MIN_SAMPLE,
        })

    # Probabilistic scoring. `pairs` is (forecast, actual) over resolved claims.
    pairs: list[tuple[float, int]] = []
    naive_pairs: list[tuple[float, int]] = []
    for claim in ledger["claims"]:
        if claim.get("outcome") is None:
            continue
        actual = 1 if claim["outcome"] == "confirmed" else 0
        forecast = claim.get("forecast_probability")
        if forecast is None:
            forecast = _clamp_probability(claim.get("score", 50) / 100)
        pairs.append((float(forecast), actual))
        naive_pairs.append((_clamp_probability(claim.get("score", 50) / 100), actual))

    # Mean gap between what a band promised and what it delivered.
    gaps = [
        abs(b["confirmation_rate"] - _clamp_probability(
            next((c["forecast_probability"] for c in ledger["claims"]
                  if c.get("band") == b["band"] and c.get("forecast_probability") is not None),
                 0.5)))
        for b in bands_out if b["confirmation_rate"] is not None
    ]
    calibration_error = round(sum(gaps) / len(gaps), 4) if gaps else None

    total_resolved = sum(b["resolved"] for b in bands_out)
    open_claims = sum(1 for c in ledger["claims"] if c["outcome"] is None)

    brier = brier_score(pairs)
    naive_brier = brier_score(naive_pairs)
    chain_ok, chain_break = verify_chain(ledger)

    # Progress against the public commitment, judged from the day the promise
    # was made — not from today, which would make any gate trivially passable.
    made = _parse_dt(COMMITMENT_MADE_AT)
    days_elapsed = (datetime.now(timezone.utc) - made).days if made else 0
    commitments_out = []
    for gate in COMMITMENTS:
        due = gate["day"] <= days_elapsed
        met_n = total_resolved >= gate["min_resolved"]
        met_b = gate["max_brier"] is None or (brier is not None and brier <= gate["max_brier"])
        commitments_out.append({
            **gate,
            "due": due,
            "resolved_so_far": total_resolved,
            "brier_so_far": brier,
            "status": ("met" if met_n and met_b else "missed") if due else "pending",
        })

    return {
        "committed_at": COMMITMENT_MADE_AT,
        "days_elapsed": days_elapsed,
        "commitments": commitments_out,
        "brier": brier,
        "brier_naive_baseline": naive_brier,
        # Positive means calibration is beating the "score/100 is a probability"
        # assumption the product makes implicitly. Negative means it is worse.
        "brier_improvement_over_naive": (
            round(naive_brier - brier, 4) if brier is not None and naive_brier is not None else None
        ),
        "log_loss": log_loss(pairs),
        "calibration_error": calibration_error,
        "chain_intact": chain_ok,
        "chain_break_at": chain_break,
        "bands": bands_out,
        "total_resolved": total_resolved,
        "open_claims": open_claims,
        "resolved_by": dict(by_resolver),
        "externally_resolved": externally_resolved,
        "external_share": round(externally_resolved / total_resolved, 3) if total_resolved else None,
        "min_sample": MIN_SAMPLE,
        "resolution_window_cycles": RESOLUTION_WINDOW_CYCLES,
        # Until a band has a rate, the page must keep saying the score is a
        # ranking position, not a probability.
        "calibrated": any(b["sufficient_sample"] for b in bands_out),
        "method": (
            "Claims are resolved after "
            f"{RESOLUTION_WINDOW_CYCLES} cycles, preferring outside evidence: an "
            "independent publisher covering the same country and topic, then a "
            "newer release of the same indicator, and only failing those, whether "
            "our own pipeline kept reporting the fact."
        ),
    }


def calibrated_label(score: int, report: dict[str, Any]) -> str:
    """Reader-facing confidence phrasing for a score."""
    label = band_for(score)
    for band in report.get("bands", []):
        if band["band"] == label and band.get("confirmation_rate") is not None:
            pct = round(band["confirmation_rate"] * 100)
            return f"{score}/100 · signals scored {label} held up {pct}% of the time"
    return f"{score}/100 · not yet calibrated — ranking position, not a probability"


def main() -> None:
    desk_path = ROOT / "outbox" / "dispatch_desk.json"
    signals_path = ROOT / "data" / "composite" / "latest.json"
    if not desk_path.exists() or not signals_path.exists():
        print("calibration: missing desk or composite signals, skipping")
        return

    cycle_id = str(json.loads(desk_path.read_text()).get("cycle_id", ""))
    if not cycle_id:
        print("calibration: desk has no cycle_id, skipping")
        return

    raw = json.loads(signals_path.read_text())
    signals = raw.get("signals") or []

    # Score through the desk's full publication path (including feedback and
    # transferred FDI magnitude) without mutating editorial state.
    signals = score_published_signals(signals)

    news_raw = json.loads((ROOT / "data" / "regional_news" / "latest.json").read_text()) \
        if (ROOT / "data" / "regional_news" / "latest.json").exists() else {}
    wb_raw = json.loads((ROOT / "data" / "world_bank" / "latest.json").read_text()) \
        if (ROOT / "data" / "world_bank" / "latest.json").exists() else {}

    ledger = record_cycle(signals, cycle_id)
    resolved = resolve_claims(
        ledger, cycle_id,
        news_items=news_raw.get("items") or [],
        observations=wb_raw.get("observations") or [],
    )
    save_ledger(ledger)

    report = reliability(ledger)
    report["cycle_id"] = cycle_id
    report["generated_at"] = _now()
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        f"calibration: {len(signals)} signals considered for {cycle_id}, "
        f"{resolved} resolved, {report['total_resolved']} total resolved, "
        f"{report['open_claims']} open -> {REPORT_FILE}"
    )


if __name__ == "__main__":
    main()
