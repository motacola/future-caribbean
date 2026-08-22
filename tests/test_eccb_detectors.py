"""Regression tests for the ECCB composite-signal detectors.

Guards against three defects found in detect_eccb_credit_surge /
detect_eccb_deposit_growth (2026-08-22):

1. Per-iteration re-declaration of the accumulator wiped earlier
   countries' signals, and an early ``return`` emitted at most ONE
   signal per call even with several qualifying countries.
2. Configured YoY growth thresholds were never applied — any country
   with bare indicator rows fired a "surge" claim.
3. "Surge"/"growth" fired off raw stock levels with no measured change.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mergers.cross_source_merger import (  # noqa: E402
    detect_ccrif_payout,
    detect_eccb_credit_surge,
    detect_eccb_deposit_growth,
)

RULES_CREDIT = {
    "conditions": {
        "private_credit_growth_pct_min": 10,
        "total_deposits_growth_pct_min": 5,
        "net_foreign_assets_growth_pct_min": 3,
    }
}
RULES_DEPOSIT = {
    "conditions": {
        "total_deposits_growth_pct_min": 3,
        "private_sector_credit_growth_pct_min": 5,
    }
}


def _obs(cc: str, indicator: str, value: float, yoy: float | None) -> dict:
    period = f"2025 (YoY: {yoy:+.1f}%)" if yoy is not None else "2025"
    return {
        "country_code": cc,
        "indicator": indicator,
        "value": value,
        "period": period,
    }


def _credit_rules_data() -> dict:
    return {"observations": [
        _obs("ECCU", "private_sector_credit", 5200, 12.0),
        _obs("ECCU", "total_deposits", 9800, 6.5),
        _obs("ECCU", "net_foreign_assets", 2100, 4.0),
    ]}


def test_credit_surge_fires_above_thresholds():
    out = detect_eccb_credit_surge(RULES_CREDIT, _credit_rules_data())
    assert len(out) == 1
    assert out[0].id == "eccb-credit-surge-eccu"
    assert "+12.0%" in out[0].summary


def test_credit_surge_accumulates_all_countries():
    """Two qualifying unions must yield TWO signals (was: exactly one)."""
    data = _credit_rules_data()
    data["observations"] += [
        _obs("XCD2", "private_sector_credit", 300, 11.0),
        _obs("XCD2", "total_deposits", 700, 5.5),
    ]
    out = detect_eccb_credit_surge(RULES_CREDIT, data)
    assert {s.id for s in out} == {"eccb-credit-surge-eccu", "eccb-credit-surge-xcd2"}


def test_credit_surge_respects_thresholds():
    """Credit growth below the configured minimum must NOT fire (was: always fired)."""
    data = _credit_rules_data()
    data["observations"][0] = _obs("ECCU", "private_sector_credit", 5200, 9.9)
    assert detect_eccb_credit_surge(RULES_CREDIT, data) == []


def test_credit_surge_requires_measured_change():
    """No YoY in the period label means no surge claim (was: fired on raw values)."""
    data = _credit_rules_data()
    for o in data["observations"]:
        o["period"] = "2025"
    assert detect_eccb_credit_surge(RULES_CREDIT, data) == []


def test_credit_surge_gates_on_nfa_when_present():
    data = _credit_rules_data()
    data["observations"][2] = _obs("ECCU", "net_foreign_assets", 2100, 2.0)
    assert detect_eccb_credit_surge(RULES_CREDIT, data) == []
    # Absent NFA series must not block the core pair.
    del data["observations"][2]
    out = detect_eccb_credit_surge(RULES_CREDIT, data)
    assert len(out) == 1


def test_deposit_growth_accumulates_and_gates():
    data = {"observations": [
        _obs("ECCU", "total_deposits", 9800, 4.2),
        _obs("ECCU", "private_sector_credit", 5200, 6.0),
        _obs("XCD2", "total_deposits", 800, 3.9),
        # Below deposit threshold — must be dropped entirely:
        _obs("XCD3", "total_deposits", 500, 2.9),
    ]}
    out = detect_eccb_deposit_growth(RULES_DEPOSIT, data)
    assert {s.id for s in out} == {"eccb-deposit-growth-eccu", "eccb-deposit-growth-xcd2"}


def test_deposit_growth_corroborates_credit_when_published():
    """Config sets private_sector_credit_growth_pct_min; weak credit suppresses."""
    data = {"observations": [
        _obs("ECCU", "total_deposits", 9800, 4.2),
        _obs("ECCU", "private_sector_credit", 5200, 4.0),
    ]}
    assert detect_eccb_deposit_growth(RULES_DEPOSIT, data) == []


# ── CCRIF member_only guard ────────────────────────────────

RULES_CCRIF = {
    "conditions": {
        "payout_usd_min": 1000000,
        "peril_match": ["tropical_cyclone", "earthquake", "excess_rainfall"],
        "ccrif_member_only": True,
    }
}


def _payout(country: str) -> dict:
    return {
        "country": country,
        "country_code": country[:2].upper(),
        "payout_usd": 5_000_000,
        "peril": "tropical_cyclone",
        "event_date": "2026-08-01",
        "announced_date": "2026-08-05",
        "policy_type": "parametric",
    }


def test_ccrif_member_payouts_pass():
    data = {"payouts": [_payout("Grenada"), _payout("St. Lucia")]}
    out = detect_ccrif_payout(RULES_CCRIF, data)
    assert len(out) == 2


def test_ccrif_nonmember_payout_suppressed():
    """The docstring promised 'member country only' — now it is enforced."""
    data = {"payouts": [_payout("Atlantis"), _payout("Grenada")]}
    out = detect_ccrif_payout(RULES_CCRIF, data)
    assert len(out) == 1
    assert out[0].countries == ["Grenada"]


def test_ccrif_guard_can_be_disabled():
    rules = dict(RULES_CCRIF)
    rules["conditions"] = dict(RULES_CCRIF["conditions"], ccrif_member_only=False)
    data = {"payouts": [_payout("Atlantis")]}
    assert len(detect_ccrif_payout(rules, data)) == 1


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
