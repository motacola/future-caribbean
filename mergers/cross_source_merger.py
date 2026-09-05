#!/usr/bin/env python3
"""Cross-source signal merger — reads all 4 watcher outputs and produces
composite intelligence signals by combining evidence across sources.

Composite rules:
  🌪️ Cyclone Risk   = buoy pressure drop + small craft advisory
  🚢 Maritime Hazard = buoy high wind + marine alert
  💼 Investment      = FDI surge + IDB project dataset
  ⚠️ Vulnerability   = high inflation + high unemployment
  🏖️ Tourism Impact  = GDP growth + weather conditions

Outputs:
  data/composite/latest.json  — all composite signals
  signals/composite/latest.md — merged signal brief
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "config" / "composite_rules.json"
DEFAULT_DATA_DIR = ROOT / "data" / "composite"
DEFAULT_SIGNAL_DIR = ROOT / "signals" / "composite"
STATE_FILE = ROOT / "data" / "composite" / ".sent_composites.json"


WB_SIGNAL = ROOT / "signals" / "world_bank" / "latest.md"
WB_DATA = ROOT / "data" / "world_bank" / "latest.json"
IDB_DATA = ROOT / "data" / "idb" / "latest.json"
NOAA_SIGNAL = ROOT / "data" / "noaa" / "latest.json"
NDBC_DATA = ROOT / "data" / "ndbc" / "latest.json"
TIER2_DATA = ROOT / "data" / "tier2" / "latest.json"
NHC_DATA = ROOT / "data" / "nhc" / "latest.json"


@dataclass(frozen=True)
class CompositeSignal:
    id: str
    kind: str
    label: str
    priority: str
    summary: str
    evidence: list[str]
    countries: list[str]
    sources: list[str]
    # Sources that say something about THIS country's claim, versus datasets
    # that merely exist for the region this cycle. Conflating the two let a
    # region-wide "CARICOM has trade data" flag count as per-country
    # corroboration for every country at once. Defaults keep older
    # constructors working; scoring falls back to `sources` when unset.
    corroborating_sources: list[str] = field(default_factory=list)
    context_sources: list[str] = field(default_factory=list)
    # Identity of the underlying fact: country + indicator + period. Two
    # signals sharing a fact_key describe the SAME observation, so they must
    # not be counted as two independent pieces of corroboration.
    fact_key: str = ""
    # The period the evidence actually describes (e.g. "2024"), which is not
    # the same as when we fetched it. World Bank series run a year or more
    # behind, and a page that says "moving now" has to be able to say so.
    observed_period: str = ""


def fdi_observation_index(wb_observations: list[dict]) -> dict[str, dict]:
    """country -> the FDI observation, so detectors can carry its period."""
    index: dict[str, dict] = {}
    for obs in wb_observations or []:
        if "DINV" not in str(obs.get("indicator_code", "")):
            continue
        country = obs.get("country_name") or ""
        if country:
            index[country] = obs
    return index


def fact_identity(country: str, obs: dict | None, fallback_indicator: str = "FDI") -> tuple[str, str]:
    """(fact_key, observed_period) for a country's observation."""
    if not obs:
        return (f"{country}|{fallback_indicator}|unknown", "")
    period = str(obs.get("year") or "")
    indicator = str(obs.get("indicator_code") or fallback_indicator)
    return (f"{country}|{indicator}|{period or 'unknown'}", period)


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ── Source readers ────────────────────────────────────────

def read_wb_observations() -> list[dict]:
    data = load_json(WB_DATA)
    if data:
        return data.get("observations", [])
    return []


def read_wb_signals_md() -> list[str]:
    if not WB_SIGNAL.exists():
        return []
    text = WB_SIGNAL.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_signals = False
    signals: list[str] = []
    for line in lines:
        if line.strip() == "## Signals":
            in_signals = True
            continue
        if in_signals:
            if line.startswith("## "):
                break
            if line.startswith("- "):
                signals.append(line[2:].strip())
    return signals


def read_idb_topics() -> list[dict]:
    data = load_json(IDB_DATA)
    if data:
        return data.get("datasets", [])
    return []


def read_noaa_alerts() -> list[dict]:
    data = load_json(NOAA_SIGNAL)
    if data:
        return data.get("alerts", [])
    return []


def read_ndbc_readings() -> list[dict]:
    data = load_json(NDBC_DATA)
    if data:
        return data.get("readings", [])
    return []


def read_ndbc_history() -> list[dict]:
    hist = load_json(ROOT / "data" / "ndbc" / "history.json")
    return list(hist.values()) if hist else []


def read_tier2_items() -> list[dict]:
    data = load_json(TIER2_DATA)
    if data:
        return data.get("items", [])
    return []


def read_nhc_data() -> dict | None:
    """Read NHC watcher output: outlook, development areas, active storms."""
    data = load_json(NHC_DATA)
    if data:
        return data.get("snapshot")
    return None


# ── Helper: country name extraction

def extract_country(signal_text: str) -> str | None:
    m = re.match(r"^([A-Za-z .]+?):", signal_text)
    return m.group(1).strip() if m else None


# ── Composite rule engines ────────────────────────────────

def detect_cyclone_risk(
    rules: dict,
    ndbc_readings: list[dict],
    noaa_alerts: list[dict],
    ndbc_history: list[dict],
) -> list[CompositeSignal]:
    """Buoy pressure drop + marine alert = cyclone risk per region."""
    cond = rules.get("conditions", {})
    max_pressure = cond.get("buoy_pressure_max", 1008)
    min_wind = cond.get("buoy_wind_min_kts", 20)
    need_advisory = cond.get("small_craft_advisory_required", False)

    # Check marine alerts
    has_marine = any(
        a.get("event") == "Small Craft Advisory" and a.get("zone_type") == "marine"
        for a in noaa_alerts
    )
    if need_advisory and not has_marine:
        return []

    signals: list[CompositeSignal] = []
    for reading in ndbc_readings:
        pres = reading.get("pressure_hpa")
        wind = reading.get("wind_speed_ms")
        wind_kts = (wind * 1.94384) if wind else None
        station = reading.get("station_name", "Unknown")

        if pres is not None and pres <= max_pressure and wind_kts is not None and wind_kts >= min_wind:
            region = reading.get("region", "caribbean")
            country_map = {"eastern": "Barbados / Windwards", "northern": "Puerto Rico / USVI", "western": "Cayman / Jamaica"}
            country = country_map.get(region, "Caribbean")

            signals.append(CompositeSignal(
                id=f"cyclone-{reading.get('station_id','?')}",
                kind="cyclone_risk",
                label="🌀 Cyclone / Severe Weather Risk",
                priority="high",
                summary=f"Elevated tropical weather risk in {country}: {station} reports {pres:.0f} hPa at {wind_kts:.0f} kts",
                evidence=[f"Buoy {station}: {pres:.0f} hPa, wind {wind_kts:.0f} kts"],
                countries=[country],
                sources=["NDBC", "NOAA"],
            ))

    return signals


def detect_maritime_hazard(
    rules: dict,
    ndbc_readings: list[dict],
    noaa_alerts: list[dict],
) -> list[CompositeSignal]:
    """High buoy wind + marine alert = confirmed maritime hazard."""
    cond = rules.get("conditions", {})
    min_wind = cond.get("buoy_wind_min_kts", 25)
    need_marine = cond.get("noaa_marine_alert_required", True)

    has_marine = any(
        a.get("event") == "Small Craft Advisory" for a in noaa_alerts
    )
    if need_marine and not has_marine:
        return []

    signals: list[CompositeSignal] = []
    for reading in ndbc_readings:
        wind = reading.get("wind_speed_ms")
        wind_kts = (wind * 1.94384) if wind else None
        station = reading.get("station_name", "Unknown")

        if wind_kts is not None and wind_kts >= min_wind:
            signals.append(CompositeSignal(
                id=f"maritime-{reading.get('station_id','?')}",
                kind="maritime_hazard",
                label="🚢 Maritime Hazard",
                priority="medium",
                summary=f"Small craft advisory active with {wind_kts:.0f} kts wind at {station}",
                evidence=[f"Buoy {station}: {wind_kts:.0f} kts", "NOAA Small Craft Advisory active"],
                countries=["Caribbean"],
                sources=["NDBC", "NOAA"],
            ))

    return signals


def detect_investment_signal(
    rules: dict,
    wb_signals: list[str],
    wb_observations: list[dict],
    idb_datasets: list[dict],
) -> list[CompositeSignal]:
    """FDI surge + IDB project dataset in same country = investment signal."""
    cond = rules.get("conditions", {})
    fdi_min = cond.get("fdi_growth_min_pct", 20)
    gdp_min = cond.get("gdp_growth_min_pct", 5)
    need_idb = cond.get("idb_topic_match_required", True)

    # Extract FDI surges from WB signals
    countries_with_fdi: dict[str, list[str]] = defaultdict(list)
    countries_with_gdp: dict[str, list[str]] = defaultdict(list)

    for sig in wb_signals:
        country = extract_country(sig)
        if not country:
            continue
        if "foreign direct investment" in sig.lower():
            # Only flag positive FDI growth (surges up, not drops)
            m = re.search(r"moved up ([\d.]+)%", sig)
            if m and float(m.group(1)) >= fdi_min:
                countries_with_fdi[country].append(sig)
        if "gdp" in sig.lower():
            m = re.search(r"([\d.]+)%", sig)
            if m and float(m.group(1)) >= gdp_min:
                countries_with_gdp[country].append(sig)

    # Cross-reference with IDB topics
    idb_countries = set()
    for ds in idb_datasets:
        for topic in ds.get("topics", []):
            if topic in ("economy", "infrastructure", "climate"):
                idb_countries.add(topic)

    fdi_index = fdi_observation_index(wb_observations)

    signals: list[CompositeSignal] = []
    for country in countries_with_fdi:
        evidence = countries_with_fdi[country]
        if need_idb and not idb_countries:
            continue
        key, period = fact_identity(country, fdi_index.get(country))
        signals.append(CompositeSignal(
            id=f"invest-{country.lower().replace(' ','-')}",
            kind="investment_signal",
            label="💼 Investment Signal",
            priority="medium",
            summary=f"{country}: FDI surge detected with active IDB development datasets available",
            evidence=evidence,
            countries=[country],
            sources=["World Bank", "IDB"],
            fact_key=key,
            observed_period=period,
        ))

    return signals


def detect_economic_vulnerability(
    rules: dict,
    wb_signals: list[str],
) -> list[CompositeSignal]:
    """High inflation + high unemployment = vulnerability."""
    cond = rules.get("conditions", {})
    infl_max = cond.get("inflation_max_pct", 10)
    unemp_max = cond.get("unemployment_max_pct", 15)

    countries_infl: dict[str, list[str]] = defaultdict(list)
    countries_unemp: dict[str, list[str]] = defaultdict(list)

    for sig in wb_signals:
        country = extract_country(sig)
        if not country:
            continue
        if "inflation" in sig.lower():
            m = re.search(r"([\d.]+)%", sig)
            if m:
                val = float(m.group(1))
                if val >= infl_max:
                    countries_infl[country].append(sig)
        if "unemployment" in sig.lower():
            m = re.search(r"([\d.]+)%", sig)
            if m:
                val = float(m.group(1))
                if val >= unemp_max:
                    countries_unemp[country].append(sig)

    signals: list[CompositeSignal] = []
    # Any country with high inflation OR unemployment => vulnerability
    for country in set(list(countries_infl.keys()) + list(countries_unemp.keys())):
        evidence = countries_infl.get(country, []) + countries_unemp.get(country, [])
        if evidence:
            signals.append(CompositeSignal(
                id=f"vuln-{country.lower().replace(' ','-')}",
                kind="economic_vulnerability",
                label="⚠️ Economic Vulnerability",
                priority="medium",
                summary=f"{country}: elevated economic vulnerability indicators",
                evidence=evidence,
                countries=[country],
                sources=["World Bank"],
            ))

    return signals


def detect_tourism_impact(
    rules: dict,
    wb_signals: list[str],
    noaa_alerts: list[dict],
) -> list[CompositeSignal]:
    """Strong GDP growth flagged but no active wind advisory = positive tourism context."""
    cond = rules.get("conditions", {})
    gdp_min = cond.get("gdp_growth_min_pct", 5)
    no_wind = cond.get("wind_advisory_active", False)

    has_wind = any("Wind Advisory" in (a.get("event", "") or "") for a in noaa_alerts)
    if no_wind and has_wind:
        return []

    countries_gdp: dict[str, list[str]] = defaultdict(list)
    for sig in wb_signals:
        country = extract_country(sig)
        if not country:
            continue
        if "gdp" in sig.lower():
            m = re.search(r"([\d.]+)%", sig)
            if m and float(m.group(1)) >= gdp_min:
                countries_gdp[country].append(sig)

    signals: list[CompositeSignal] = []
    for country, evidence in countries_gdp.items():
        signals.append(CompositeSignal(
            id=f"tourism-{country.lower().replace(' ','-')}",
            kind="tourism_impact",
            label="🏖️ Tourism Impact",
            priority="low",
            summary=f"{country}: strong GDP growth ({evidence[0].split(':')[1].strip() if ':' in evidence[0] else ''}) — positive tourism context",
            evidence=evidence,
            countries=[country],
            sources=["World Bank"],
        ))
    return signals


def detect_food_security(
    rules: dict,
    tier2_items: list[dict],
    wb_signals: list[str],
) -> list[CompositeSignal]:
    """CARICOM food trade data + inflation context = food security signal."""
    cond = rules.get("conditions", {})
    min_food_datasets = cond.get("caricom_food_trade_min_datasets", 2)
    check_inflation = cond.get("cross_reference_inflation", True)
    infl_threshold = cond.get("inflation_threshold_pct", 5)

    # Find CARICOM food-related datasets
    food_items = [
        i for i in tier2_items
        if i.get("source_slug") == "caricom"
        and i.get("item_type") == "country_data"
        and any(kw in (i.get("title", "") or "").lower()
                for kw in ["food", "import", "export", "agriculture"])
    ]

    if len(food_items) < min_food_datasets:
        return []

    # Cross-reference with inflation signals from WB
    high_inflation_countries: list[str] = []
    if check_inflation:
        for sig in wb_signals:
            country = extract_country(sig)
            if not country:
                continue
            if "inflation" in sig.lower():
                m = re.search(r"([\d.]+)%", sig)
                if m and float(m.group(1)) >= infl_threshold:
                    high_inflation_countries.append(country)

    evidence = [
        f"CARICOM food trade data: {len(food_items)} datasets available",
    ]
    for fi in food_items[:3]:
        evidence.append(f"• {fi['title']}")

    vuln_context = ""
    if high_inflation_countries:
        vuln_context = f" — elevated inflation in {', '.join(high_inflation_countries[:3])}"
        evidence.append(f"Inflation > {infl_threshold}% in: {', '.join(high_inflation_countries[:3])}")

    signals: list[CompositeSignal] = []
    signals.append(CompositeSignal(
        id="food-security-regional",
        kind="food_security",
        label="🌾 Food Security Signal",
        priority="medium",
        summary=f"Regional food trade monitoring active: {len(food_items)} datasets{vuln_context}",
        evidence=evidence,
        countries=["CARICOM"],
        sources=["CARICOM", "World Bank"],
    ))
    return signals


def detect_development_pipeline(
    rules: dict,
    tier2_items: list[dict],
    idb_datasets: list[dict],
) -> list[CompositeSignal]:
    """CDB procurement notices + IDB infrastructure datasets = active development pipeline."""
    cond = rules.get("conditions", {})
    need_procurement = cond.get("cdb_procurement_active", True)
    need_infra = cond.get("idb_infrastructure_match", True)

    # Find CDB procurement notices
    cdb_procurement = [
        i for i in tier2_items
        if i.get("source_slug") == "cdb" and i.get("item_type") == "procurement"
    ]

    if need_procurement and not cdb_procurement:
        return []

    # Find IDB infrastructure datasets
    idb_infra = [
        ds for ds in idb_datasets
        if "infrastructure" in ds.get("topics", [])
    ] if need_infra else []

    if need_infra and not idb_infra:
        return []

    evidence = []
    if cdb_procurement:
        evidence.append(f"CDB active procurement notices: {len(cdb_procurement)}")
        for p in cdb_procurement[:3]:
            evidence.append(f"• {p['title']}")
    if idb_infra:
        evidence.append(f"IDB infrastructure datasets: {len(idb_infra)}")

    signals: list[CompositeSignal] = []
    signals.append(CompositeSignal(
        id="dev-pipeline-regional",
        kind="development_pipeline",
        label="🏗️ Development Pipeline",
        priority="medium",
        summary=f"Active development pipeline: {len(cdb_procurement)} CDB procurements + {len(idb_infra)} IDB infrastructure datasets",
        evidence=evidence,
        countries=["CARICOM"],
        sources=["CDB", "IDB"],
    ))
    return signals


def detect_enhanced_investment(
    rules: dict,
    wb_signals: list[str],
    tier2_items: list[dict],
    wb_observations: list[dict] | None = None,
) -> list[CompositeSignal]:
    """Triple-source validation: WB FDI surge + CARICOM trade data + CDB activity."""
    cond = rules.get("conditions", {})
    fdi_min = cond.get("wb_fdi_growth_min_pct", 20)
    need_trade = cond.get("caricom_trade_data_available", True)
    need_cdb = cond.get("cdb_procurement_or_evaluation", True)
    require_two = cond.get("require_two_of_three", True)

    # Source 1: WB FDI surges
    countries_fdi: list[str] = []
    for sig in wb_signals:
        country = extract_country(sig)
        if not country:
            continue
        if "foreign direct investment" in sig.lower():
            m = re.search(r"moved up ([\d.]+)%", sig)
            if m and float(m.group(1)) >= fdi_min:
                countries_fdi.append(country)

    if not countries_fdi:
        return []

    # Source 2: CARICOM trade data availability
    has_caricom_trade = False
    if need_trade:
        trade_titles = " ".join(
            i.get("title", "") for i in tier2_items
            if i.get("source_slug") == "caricom"
        ).lower()
        has_caricom_trade = any(kw in trade_titles for kw in ["trade", "import", "export", "fdi"])

    # Source 3: CDB activity
    has_cdb_activity = False
    if need_cdb:
        has_cdb_activity = any(
            i.get("source_slug") == "cdb"
            for i in tier2_items
        )

    # has_caricom_trade and has_cdb_activity are region-wide: they say a
    # dataset exists this cycle, not that it says anything about a given
    # country. They are therefore context, never corroboration — computing
    # them once outside the loop handed every country the same two "sources"
    # and made three unrelated markets score identically.
    context_available = [
        name for name, present in (("CARICOM", has_caricom_trade), ("CDB", has_cdb_activity))
        if present
    ]
    if require_two and not countries_fdi:
        return []

    fdi_index = fdi_observation_index(wb_observations or [])
    enhanced_facts = {c: fact_identity(c, fdi_index.get(c)) for c in countries_fdi}

    signals: list[CompositeSignal] = []
    for country in countries_fdi:
        # Only the World Bank observation is country-specific here.
        corroborating = ["World Bank"]
        sources_list = corroborating + context_available
        evidence_parts = [f"WB FDI surge detected: {country}"]
        if has_caricom_trade:
            evidence_parts.append("CARICOM trade/FDI data available (regional context, not country confirmation)")
        if has_cdb_activity:
            evidence_parts.append("CDB procurement/evaluation activity (regional context, not country confirmation)")
        evidence_parts.append(
            f"Confidence: {len(corroborating)} country-specific source confirmed"
            + (f" · {len(context_available)} regional dataset(s) available as context" if context_available else "")
        )

        signals.append(CompositeSignal(
            id=f"enhanced-invest-{country.lower().replace(' ','-')}",
            kind="enhanced_investment",
            label="💎 Enhanced Investment Signal",
            priority="medium",
            summary=(
                f"{country}: World Bank FDI surge"
                + (f", with {len(context_available)} regional dataset(s) available as context"
                   if context_available else "")
            ),
            evidence=evidence_parts,
            countries=[country],
            sources=sources_list,
            corroborating_sources=list(corroborating),
            context_sources=list(context_available),
            # Same World Bank observation as the investment_signal for this
            # country — one fact, described twice.
            fact_key=enhanced_facts.get(country, (f"{country}|FDI|unknown", ""))[0],
            observed_period=enhanced_facts.get(country, ("", ""))[1],
        ))

    return signals


# ── Supply Chain Signal ─────────────────────────────────────


def detect_supply_chain_signal(
    rules: dict,
    tier2_items: list[dict],
    ndbc_readings: list[dict],
    noaa_alerts: list[dict],
) -> list[CompositeSignal]:
    """CDB procurement + stable maritime conditions + Tier 2 logistics data = supply chain opportunity.

    Conditions:
      - CDB procurement active (from tier2_items)
      - NDBC maritime stable (no high winds, no marine alerts)
      - Tier 2 logistics data available (CARICOM transport/trade data)
    """
    cond = rules.get("conditions", {})
    need_procurement = cond.get("cdb_procurement_active", True)
    need_maritime_stable = cond.get("ndbc_maritime_stable", True)
    need_logistics = cond.get("tier2_logistics_data_available", True)

    # Source 1: CDB procurement notices
    cdb_procurement = [
        i for i in tier2_items
        if i.get("source_slug") == "cdb" and i.get("item_type") == "procurement"
    ]
    if need_procurement and not cdb_procurement:
        return []

    # Source 2: Maritime stability (no high winds, no marine alerts)
    maritime_stable = True
    if need_maritime_stable:
        high_wind = any(
            (r.get("wind_speed_ms") or 0) * 1.94384 >= 25
            for r in ndbc_readings
        )
        marine_alert = any(
            a.get("event") in ("Small Craft Advisory", "Gale Warning", "Storm Warning")
            for a in noaa_alerts
            if a.get("zone_type") == "marine"
        )
        if high_wind or marine_alert:
            maritime_stable = False

    if need_maritime_stable and not maritime_stable:
        return []

    # Source 3: Tier 2 logistics data (CARICOM transport/trade)
    logistics_items = []
    has_logistics = False
    if need_logistics:
        logistics_items = [
            i for i in tier2_items
            if i.get("source_slug") == "caricom"
            and any(kw in (i.get("title", "") or "").lower()
                    for kw in ["transport", "shipping", "port", "logistics", "trade", "import", "export"])
        ]
        has_logistics = len(logistics_items) >= 1

    if need_logistics and not has_logistics:
        return []

    # All conditions met - build signal
    evidence = []
    sources = ["CDB", "NDBC"]
    if cdb_procurement:
        evidence.append(f"CDB active procurement notices: {len(cdb_procurement)}")
        for p in cdb_procurement[:2]:
            evidence.append(f"  • {p['title'][:80]}")
    if maritime_stable:
        evidence.append("Maritime conditions stable — no high-wind or marine alerts")
    if has_logistics:
        evidence.append(f"CARICOM logistics/trade data available: {len(logistics_items)} dataset(s)")
        sources.append("CARICOM")

    # Determine affected corridor
    corridor = "CARICOM regional"
    if cdb_procurement:
        # Check if any procurement mentions specific countries
        countries_mentioned = set()
        for p in cdb_procurement:
            title = (p.get("title", "") or "").lower()
            for country in ["guyana", "suriname", "trinidad", "barbados", "jamaica", "belize",
                           "bahamas", "dominica", "grenada", "saint lucia", "st. vincent",
                           "st. kitts", "antigua", "cayman"]:
                if country in title:
                    countries_mentioned.add(country.title())
        if countries_mentioned:
            corridor = ", ".join(sorted(countries_mentioned))

    signals: list[CompositeSignal] = []
    signals.append(CompositeSignal(
        id=f"supply-chain-{corridor.lower().replace(' ', '-').replace(',', '')}",
        kind="supply_chain_signal",
        label="🔗 Supply Chain Opportunity",
        priority="medium",
        summary=f"Supply chain corridor opportunity: {corridor} — CDB procurement active + maritime stable + logistics data available",
        evidence=evidence,
        countries=[corridor] if corridor != "CARICOM regional" else ["CARICOM"],
        sources=sources,
    ))
    return signals


# ── AIS Maritime Signals ─────────────────────────────────────


def detect_port_activity_surge(
    rules: dict,
    ais_data: dict,
) -> list[CompositeSignal]:
    """Port activity surge from AIS vessel density.

    Conditions:
      - Vessel count at any monitored port >= threshold
      - Port must be in the monitored Caribbean port list
    """
    cond = rules.get("conditions", {})
    vessel_min = cond.get("vessel_count_min", 15)
    port_list = cond.get("port_list", [])

    ports_data = ais_data.get("ports", {}) if ais_data else {}
    if not ports_data:
        return []

    signals: list[CompositeSignal] = []
    for port_name, port_data in ports_data.items():
        if port_list and port_name not in port_list:
            continue

        vessel_count = port_data.get("vessel_count", 0)
        if vessel_count < vessel_min:
            continue

        avg_sog = port_data.get("avg_sog", 0)
        port_vessels = port_data.get("vessels", [])

        # Get country from port config
        port_country = ""
        for port in PORTS_CONFIG:
            if port["name"] == port_name:
                port_country = port["country"]
                break

        signals.append(CompositeSignal(
            id=f"port-activity-{port_name.lower().replace(' ', '-')}",
            kind="port_activity_surge",
            label="🚢 Port Activity Surge",
            priority="medium",
            summary=f"{port_name} ({port_country}): {vessel_count} vessels in port zone — throughput surge",
            evidence=[
                f"Port: {port_name}, {port_country}",
                f"Vessel count: {vessel_count}",
                f"Avg speed over ground: {avg_sog:.1f} kt",
                f"Collection window: {ais_data.get('collection_window_seconds', 0)}s",
            ],
            countries=[port_country] if port_country else [port_name],
            sources=["AISstream.io"],
        ))
    return signals


def detect_port_congestion(
    rules: dict,
    ais_data: dict,
) -> list[CompositeSignal]:
    """Port congestion from slow-moving vessels in port zone.

    Conditions:
      - Slow vessel count (SOG < threshold) >= minimum
      - Indicates vessels waiting/anchored = congestion
    """
    cond = rules.get("conditions", {})
    slow_min = cond.get("slow_vessel_count_min", 5)
    speed_threshold = cond.get("speed_threshold_kts", 3.0)

    ais_signals = ais_data.get("signals", []) if ais_data else []
    if not ais_signals:
        return []

    signals: list[CompositeSignal] = []
    for sig in ais_signals:
        if sig.get("type") != "port_congestion":
            continue

        port_name = sig.get("port", "")
        slow_count = sig.get("slow_vessels", 0)
        avg_sog = sig.get("avg_sog_kn", 0)

        if slow_count < slow_min:
            continue

        signals.append(CompositeSignal(
            id=f"port-congestion-{port_name.lower().replace(' ', '-')}",
            kind="port_congestion",
            label="🚧 Port Congestion",
            priority="high",
            summary=f"{port_name}: {slow_count} vessels moving < {speed_threshold} kt — congestion detected",
            evidence=[
                f"Port: {port_name}",
                f"Slow vessels (< {speed_threshold} kt): {slow_count}",
                f"Avg speed in zone: {avg_sog:.1f} kt",
                "Likely cause: anchorage waiting, berth queue, or weather delay",
            ],
            countries=[port_name],
            sources=["AISstream.io"],
        ))
    return signals


def detect_shipping_corridor(
    rules: dict,
    ais_data: dict,
) -> list[CompositeSignal]:
    """Shipping corridor detection from vessel traffic patterns.

    Conditions:
      - Vessel count in latitude band >= threshold
      - Consistent eastbound or westbound direction
    """
    cond = rules.get("conditions", {})
    vessel_min = cond.get("vessel_count_min", 20)
    valid_directions = cond.get("direction", ["eastbound", "westbound"])

    ais_corridors = ais_data.get("corridors", []) if ais_data else {}
    if not ais_corridors:
        return []

    signals: list[CompositeSignal] = []
    for corridor in ais_corridors:
        if corridor.get("direction") not in valid_directions:
            continue

        vessel_count = corridor.get("vessel_count", 0)
        if vessel_count < vessel_min:
            continue

        lat_band = corridor.get("lat_band", 0)
        direction = corridor.get("direction", "unknown")
        avg_course = corridor.get("avg_course", 0)

        signals.append(CompositeSignal(
            id=f"shipping-corridor-lat{int(lat_band)}-{direction}",
            kind="shipping_corridor",
            label="🛳️ Shipping Corridor Active",
            priority="low",
            summary=f"Lat {lat_band}°: {vessel_count} vessels on {direction} corridor (avg course {avg_course:.0f}°)",
            evidence=[
                f"Latitude band: {lat_band}°",
                f"Vessel count: {vessel_count}",
                f"Direction: {direction} (avg course {avg_course:.1f}°)",
                "Indicates established trade lane — reliable logistics corridor",
            ],
            countries=["Caribbean/Atlantic"],
            sources=["AISstream.io"],
        ))
    return signals


PORTS_CONFIG = [
    {"name": "Kingston", "country": "Jamaica", "lat": 17.97, "lon": -76.80, "bbox_radius_km": 50},
    {"name": "Port of Spain", "country": "Trinidad", "lat": 10.65, "lon": -61.52, "bbox_radius_km": 50},
    {"name": "Bridgetown", "country": "Barbados", "lat": 13.10, "lon": -59.62, "bbox_radius_km": 50},
    {"name": "Georgetown", "country": "Guyana", "lat": 6.80, "lon": -58.15, "bbox_radius_km": 50},
    {"name": "San Juan", "country": "Puerto Rico", "lat": 18.45, "lon": -66.10, "bbox_radius_km": 50},
    {"name": "Nassau", "country": "Bahamas", "lat": 25.08, "lon": -77.34, "bbox_radius_km": 50},
    {"name": "Port-au-Prince", "country": "Haiti", "lat": 18.55, "lon": -72.33, "bbox_radius_km": 50},
    {"name": "St. George's", "country": "Grenada", "lat": 12.05, "lon": -61.75, "bbox_radius_km": 50},
    {"name": "Castries", "country": "St. Lucia", "lat": 14.01, "lon": -60.99, "bbox_radius_km": 50},
    {"name": "Roseau", "country": "Dominica", "lat": 15.30, "lon": -61.38, "bbox_radius_km": 50},
]


# ── NHC Storm Risk ─────────────────────────────────────────


# ── CCRIF Payout Signal ─────────────────────────────────────


def detect_ccrif_payout(
    rules: dict,
    ccrif_data: dict,
) -> list[CompositeSignal]:
    """CCRIF parametric insurance payout = verified hazard + capital inflow signal.

    Conditions:
      - CCRIF payout >= threshold USD
      - Peril matches tropical cyclone, earthquake, or excess rainfall
      - Member country only
    """
    cond = rules.get("conditions", {})
    payout_min = cond.get("payout_usd_min", 1000000)
    peril_match = cond.get("peril_match", ["tropical_cyclone", "earthquake", "excess_rainfall"])
    member_only = cond.get("ccrif_member_only", True)

    # CCRIF government membership, cited from ccrif.org/about-us
    # (19 Caribbean + 4 Central American governments). Matched on a
    # normalised name so poller spellings ("St. Lucia" vs "Saint Lucia",
    # "St. Kitts & Nevis") still resolve. Utilities/other members are not
    # country payouts and stay out of the list.
    CCRIF_MEMBER_COUNTRIES = {
        "anguilla", "antigua and barbuda", "antigua & barbuda", "antigua",
        "the bahamas", "bahamas", "barbados", "belize", "bermuda",
        "british virgin islands", "cayman islands", "dominica", "grenada",
        "haiti", "jamaica", "montserrat", "st kitts and nevis",
        "st kitts & nevis", "st. kitts and nevis", "saint kitts and nevis",
        "saint kitts & nevis", "st lucia", "st. lucia", "saint lucia",
        "sint maarten", "st martin", "st. maarten",
        "st vincent and the grenadines", "st vincent & the grenadines",
        "st. vincent and the grenadines", "st vincent", "st. vincent",
        "saint vincent and the grenadines", "trinidad and tobago",
        "trinidad & tobago", "turks and caicos islands",
        "turks & caicos islands", "turks and caicos", "guatemala",
        "honduras", "nicaragua", "panama",
    }

    def _is_member(country_name: str) -> bool:
        normalized = re.sub(r"[^a-z& ]", "", (country_name or "").lower()).strip()
        return normalized in CCRIF_MEMBER_COUNTRIES

    payouts = ccrif_data.get("payouts", []) if ccrif_data else []
    if not payouts:
        return []

    signals: list[CompositeSignal] = []
    for payout in payouts:
        payout_usd = payout.get("payout_usd", 0)
        peril = payout.get("peril", "unknown")

        if payout_usd < payout_min:
            continue
        if peril not in peril_match:
            continue

        country_code = payout.get("country_code", "unknown")
        country = payout.get("country", "unknown")

        if member_only and not _is_member(country):
            continue

        signals.append(CompositeSignal(
            id=f"ccrif-payout-{country_code.lower()}-{peril.lower()}-{payout.get('event_date', 'unknown')}",
            kind="ccrif_payout",
            label="💰 Parametric Insurance Payout",
            priority="high",
            summary=f"{country}: CCRIF parametric payout US${payout_usd:,.0f} for {peril.replace('_', ' ')}",
            evidence=[
                f"Payout: US${payout_usd:,.0f}",
                f"Peril: {peril}",
                f"Event date: {payout.get('event_date', 'unknown')}",
                f"Announced: {payout.get('announced_date', 'unknown')}",
                f"Policy: {payout.get('policy_type', 'parametric')}",
            ],
            countries=[country],
            sources=["CCRIF SPC"],
        ))
    return signals


# ── ECCB Signals ────────────────────────────────────────────


def _eccb_growth_pct(obs: dict | None) -> float | None:
    """Parse the YoY growth the poller embeds in the period label.

    ECCB observations carry values like ``{"period": "2025 (YoY: +7.4%)"}``.
    Without a measured change we return None — a "surge"/"growth" claim
    must never fire off raw stock levels alone.
    """
    if not obs:
        return None
    m = re.search(r"YoY:\s*([+-]?\d+(?:\.\d+)?)%", str(obs.get("period", "")))
    return float(m.group(1)) if m else None


def detect_eccb_credit_surge(
    rules: dict,
    eccb_data: dict,
) -> list[CompositeSignal]:
    """ECCB private sector credit surge = banking confidence signal.

    Conditions:
      - Private sector credit growth >= threshold %
      - Total deposits growth >= threshold %
      - Net foreign assets growth >= threshold % (when NFA data is present)
    """
    cond = rules.get("conditions", {})
    credit_min = cond.get("private_credit_growth_pct_min", 10)
    deposits_min = cond.get("total_deposits_growth_pct_min", 5)
    nfa_min = cond.get("net_foreign_assets_growth_pct_min", 3)

    observations = eccb_data.get("observations", []) if eccb_data else []
    if not observations:
        return []

    credit_items = [o for o in observations if o.get("indicator") == "private_sector_credit"]
    deposit_items = [o for o in observations if o.get("indicator") == "total_deposits"]
    nfa_items = [o for o in observations if o.get("indicator") == "net_foreign_assets"]

    # Group by country (one observation per indicator/country today, but
    # keep the latest if several ever appear).
    by_country: dict[str, dict] = {}
    for item in credit_items:
        cc = item.get("country_code", "")
        if cc:
            by_country.setdefault(cc, {})["credit"] = item
    for item in deposit_items:
        cc = item.get("country_code", "")
        if cc:
            by_country.setdefault(cc, {})["deposits"] = item
    for item in nfa_items:
        cc = item.get("country_code", "")
        if cc:
            by_country.setdefault(cc, {})["nfa"] = item

    signals: list[CompositeSignal] = []
    for cc, items in by_country.items():
        credit = items.get("credit")
        deposits = items.get("deposits")
        nfa = items.get("nfa")
        if credit is None or deposits is None:
            continue

        credit_growth = _eccb_growth_pct(credit)
        deposits_growth = _eccb_growth_pct(deposits)
        nfa_growth = _eccb_growth_pct(nfa)

        # Credit + deposits are the core pair; NFA is evaluated only when
        # the union publishes it (it frequently lags the other series).
        if credit_growth is None or deposits_growth is None:
            continue
        if credit_growth < credit_min or deposits_growth < deposits_min:
            continue
        if nfa is not None and (nfa_growth is None or nfa_growth < nfa_min):
            continue

        signals.append(CompositeSignal(
            id=f"eccb-credit-surge-{cc.lower()}",
            kind="eccb_credit_surge",
            label="🏦 ECCB Private Credit Surge",
            priority="medium",
            summary=(
                f"{credit.get('country', cc)}: Private sector credit {credit_growth:+.1f}% "
                f"(EC${credit.get('value', 0):,.1f}M) + deposits {deposits_growth:+.1f}% "
                f"(EC${deposits.get('value', 0):,.1f}M) — banking expansion signal"
            ),
            evidence=[
                f"Private sector credit growth: {credit_growth:+.1f}% YoY (threshold {credit_min}%)",
                f"Total deposits growth: {deposits_growth:+.1f}% YoY (threshold {deposits_min}%)",
                (
                    f"Net foreign assets growth: {nfa_growth:+.1f}% YoY (threshold {nfa_min}%)"
                    if nfa is not None and nfa_growth is not None
                    else "NFA: data available in reports"
                ),
                f"Period: {credit.get('period', 'latest')}",
            ],
            countries=[credit.get("country", cc)],
            sources=["ECCB"],
        ))
    return signals


def detect_eccb_deposit_growth(
    rules: dict,
    eccb_data: dict,
) -> list[CompositeSignal]:
    """ECCB deposit growth = currency union stability signal.

    Conditions:
      - Total deposits growth >= threshold %
      - Private sector credit growth >= threshold %
    """
    cond = rules.get("conditions", {})
    deposits_min = cond.get("total_deposits_growth_pct_min", 3)
    credit_min = cond.get("private_sector_credit_growth_pct_min", 5)

    observations = eccb_data.get("observations", []) if eccb_data else []
    if not observations:
        return []

    deposit_items = [o for o in observations if o.get("indicator") == "total_deposits"]
    credit_by_cc = {
        o.get("country_code", ""): o
        for o in observations
        if o.get("indicator") == "private_sector_credit"
    }

    signals: list[CompositeSignal] = []
    for dep in deposit_items:
        cc = dep.get("country_code", "")
        if not cc:
            continue

        deposits_growth = _eccb_growth_pct(dep)
        if deposits_growth is None or deposits_growth < deposits_min:
            continue

        # Credit corroboration applies whenever the union publishes the
        # companion series; deposits alone can still qualify without it.
        credit = credit_by_cc.get(cc)
        credit_growth = _eccb_growth_pct(credit)
        if credit is not None and (credit_growth is None or credit_growth < credit_min):
            continue

        evidence = [
            f"Total deposits growth: {deposits_growth:+.1f}% YoY (threshold {deposits_min}%)",
            f"Total deposits: EC${dep.get('value', 0):,.1f}M",
        ]
        if credit is not None and credit_growth is not None:
            evidence.insert(1, f"Private sector credit growth: {credit_growth:+.1f}% YoY (threshold {credit_min}%)")
        evidence.append(f"Period: {dep.get('period', 'latest')}")

        signals.append(CompositeSignal(
            id=f"eccb-deposit-growth-{cc.lower()}",
            kind="eccb_deposit_growth",
            label="🏦 ECCB Deposit Growth",
            priority="medium",
            summary=(
                f"{dep.get('country', cc)}: Deposits {deposits_growth:+.1f}% YoY "
                f"(EC${dep.get('value', 0):,.1f}M) — currency union stability signal"
            ),
            evidence=evidence,
            countries=[dep.get("country", cc)],
            sources=["ECCB"],
        ))
    return signals


# ── NHC Storm Risk ─────────────────────────────────────────


def detect_nhc_storm_risk(
    rules: dict,
    nhc_data: dict | None,
    noaa_alerts: list[dict],
    ndbc_readings: list[dict],
) -> list[CompositeSignal]:
    """NHC development areas + active storms + marine conditions = storm risk signal.

    Off-season (no development areas, no active storms) produces no signals.
    During active season, checks for:
      - NHC development areas (low/med/high probability)
      - Active named storms
      - Cross-reference with NOAA marine alerts and buoy readings
    """
    if not nhc_data:
        return []

    cond = rules.get("conditions", {})
    min_prob = cond.get("min_probability", "low")

    development_areas = nhc_data.get("development_areas", [])
    active_storms = nhc_data.get("active_storms", [])
    summary = nhc_data.get("summary", "")

    prob_rank = {"high": 3, "medium": 2, "low": 1}

    signals: list[CompositeSignal] = []

    # 1. Signal for high-probability development areas
    high_areas = [
        a for a in development_areas
        if prob_rank.get(a.get("probability", "low"), 0) >= prob_rank.get(min_prob, 1)
    ]
    medium_areas = [
        a for a in development_areas if a.get("probability") == "medium"
    ]

    if high_areas:
        area_labels = [a["label"] for a in high_areas[:2]]
        evidence_parts = [
            f"NHC high-probability development: {'; '.join(area_labels)}"
        ]
        for a in high_areas:
            loc = a.get("location", "")
            if loc:
                evidence_parts.append(f"  Location: {loc}")
            desc = a.get("description", "")
            if desc:
                evidence_parts.append(f"  Details: {desc[:200]}")

        # Cross-reference with marine alerts
        marine_alerts = [
            a for a in noaa_alerts
            if a.get("zone_type") == "marine" and a.get("severity") in ("Severe", "Extreme")
        ]
        if marine_alerts:
            evidence_parts.append(f"NOAA marine alerts active: {len(marine_alerts)} zone(s)")
            sources = ["NHC", "NOAA"]
        else:
            sources = ["NHC"]

        signals.append(CompositeSignal(
            id=f"nhc-high-development-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            kind="tropical_development",
            label="🌀 Tropical Development Watch",
            priority="high",
            summary=f"NHC: {len(high_areas)} high-probability development area(s) — {summary[:120]}",
            evidence=evidence_parts,
            countries=["Caribbean/Atlantic"],
            sources=sources,
        ))

    elif medium_areas:
        evidence_parts = [
            f"NHC medium-probability development: {len(medium_areas)} area(s) being monitored"
        ]
        for a in medium_areas[:2]:
            loc = a.get("location", "")
            if loc:
                evidence_parts.append(f"  {a['label'][:80]} — {loc}")

        signals.append(CompositeSignal(
            id=f"nhc-medium-development-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            kind="tropical_development",
            label="🌀 Tropical Development Monitor",
            priority="medium",
            summary=f"NHC monitoring {len(medium_areas)} medium-probability development area(s)",
            evidence=evidence_parts,
            countries=["Caribbean/Atlantic"],
            sources=["NHC"],
        ))

    # 2. Signal for active named storms
    for storm in active_storms:
        storm_name = storm.get("name", "Unnamed")
        storm_type = storm.get("storm_type", "Tropical Cyclone")
        wind = storm.get("wind_kts")
        pressure = storm.get("pressure_mb")
        lat = storm.get("lat")
        lon = storm.get("lon")

        evidence_parts = [f"{storm_type} {storm_name} active in Atlantic basin"]
        if wind:
            evidence_parts.append(f"  Winds: {wind} kt ({wind * 1.151} mph)")
        if pressure:
            evidence_parts.append(f"  Pressure: {pressure} mb")
        if lat and lon:
            evidence_parts.append(f"  Position: {lat}°N {lon}°W")

        signals.append(CompositeSignal(
            id=f"storm-{storm_name.lower().replace(' ','-')}",
            kind="active_storm",
            label="🌀 Active Storm: " + storm_name,
            priority="high",
            summary=f"{storm_type} {storm_name}: {wind or '?'} kt, {pressure or '?'} mb — active in Caribbean/Atlantic basin",
            evidence=evidence_parts,
            countries=["Caribbean/Atlantic"],
            sources=["NHC", "NOAA"],
        ))

    return signals


# ── Output ────────────────────────────────────────────────

def write_outputs(
    signals: list[CompositeSignal],
    data_dir: Path,
    signal_dir: Path,
) -> tuple[Path, Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    signal_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}

    payload = {
        "source": "cross-source merger",
        "fetched_at": fetched_at,
        "composite_signals": len(signals),
        "signals": [asdict(s) for s in signals],
    }

    json_path = data_dir / "latest.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md_lines = [
        "# Abeng — Composite Intelligence",
        "",
        f"- Generated: {fetched_at}",
        f"- Composite signals: {len(signals)}",
        "- Sources: World Bank, IDB, NOAA NWS, NDBC Buoys, CARICOM, CDB, CCRIF, ECCB, AISstream.io",
        "",
    ]

    if not signals:
        md_lines.append("*No composite signals generated.* Normal conditions across all sources.")
        md_lines.append("")

    for sig in sorted(signals, key=lambda s: priority_order.get(s.priority, 99)):
        icon_map = {
            "cyclone_risk": "🌀", "maritime_hazard": "🚢",
            "investment_signal": "💼", "economic_vulnerability": "⚠️",
            "tourism_impact": "🏖️", "food_security": "🌾",
            "development_pipeline": "🏗️", "enhanced_investment": "💎",
            "supply_chain_signal": "🔗", "tropical_development": "🌪️", "active_storm": "🌀",
            "ccrif_payout": "💰", "eccb_credit_surge": "🏦", "eccb_deposit_growth": "🏦",
            "port_activity_surge": "🚢", "port_congestion": "🚧", "shipping_corridor": "🛳️",
        }
        icon = icon_map.get(sig.kind, "•")
        priority_badge = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sig.priority, "⚪")

        md_lines.append(f"{priority_badge} {icon} **{sig.label}**")
        md_lines.append(f"   {sig.summary}")
        md_lines.append(f"   Sources: {', '.join(sig.sources)}")
        for ev in sig.evidence[:2]:
            md_lines.append(f"   • {ev}")
        md_lines.append("")

    md_lines.append("---")
    md_lines.append(f"**Composite signals:** {len(signals)}")
    md_lines.append("*Generated by cross-source merger — combines evidence across 6 watchers*")

    md_path = signal_dir / "latest.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path


def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_state(ids: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(ids), indent=2) + "\n", encoding="utf-8")


def run(rules_path: Path, data_dir: Path, signal_dir: Path) -> int:
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    combined_rules = rules.get("composite_rules", {})

    # Read all source data
    wb_obs = read_wb_observations()
    wb_sigs = read_wb_signals_md()
    idb_ds = read_idb_topics()
    noaa_alerts = read_noaa_alerts()
    ndbc_readings = read_ndbc_readings()
    ndbc_history = read_ndbc_history()
    nhc_data = read_nhc_data()

    all_signals: list[CompositeSignal] = []

    # Read Tier 2 data
    tier2_items = read_tier2_items()

    cyclone_rules = combined_rules.get("cyclone_risk", {})
    all_signals.extend(detect_cyclone_risk(cyclone_rules, ndbc_readings, noaa_alerts, ndbc_history))

    maritime_rules = combined_rules.get("maritime_hazard", {})
    all_signals.extend(detect_maritime_hazard(maritime_rules, ndbc_readings, noaa_alerts))

    invest_rules = combined_rules.get("investment_signal", {})
    all_signals.extend(detect_investment_signal(invest_rules, wb_sigs, wb_obs, idb_ds))

    vuln_rules = combined_rules.get("economic_vulnerability", {})
    all_signals.extend(detect_economic_vulnerability(vuln_rules, wb_sigs))

    tourism_rules = combined_rules.get("tourism_impact", {})
    all_signals.extend(detect_tourism_impact(tourism_rules, wb_sigs, noaa_alerts))

    # Tier 2-enhanced rules
    food_rules = combined_rules.get("food_security", {})
    if tier2_items:
        all_signals.extend(detect_food_security(food_rules, tier2_items, wb_sigs))

    dev_rules = combined_rules.get("development_pipeline", {})
    if tier2_items:
        all_signals.extend(detect_development_pipeline(dev_rules, tier2_items, idb_ds))

    enhanced_rules = combined_rules.get("enhanced_investment", {})
    if tier2_items:
        all_signals.extend(detect_enhanced_investment(enhanced_rules, wb_sigs, tier2_items, wb_obs))

    # Supply chain signal (Tier 2 + maritime + NDBC)
    supply_chain_rules = combined_rules.get("supply_chain_signal", {})
    if tier2_items:
        all_signals.extend(detect_supply_chain_signal(supply_chain_rules, tier2_items, ndbc_readings, noaa_alerts))

    # CCRIF payout signal
    ccrif_rules = combined_rules.get("ccrif_payout", {})
    ccrif_data = load_json(ROOT / "data" / "ccrif" / "latest.json")
    if ccrif_data:
        all_signals.extend(detect_ccrif_payout(ccrif_rules, ccrif_data))

    # ECCB signals
    eccb_rules_credit = combined_rules.get("eccb_credit_surge", {})
    eccb_rules_deposit = combined_rules.get("eccb_deposit_growth", {})
    eccb_data = load_json(ROOT / "data" / "eccb" / "latest.json")
    if eccb_data:
        all_signals.extend(detect_eccb_credit_surge(eccb_rules_credit, eccb_data))
        all_signals.extend(detect_eccb_deposit_growth(eccb_rules_deposit, eccb_data))

    # AIS Maritime signals
    ais_rules_activity = combined_rules.get("port_activity_surge", {})
    ais_rules_congestion = combined_rules.get("port_congestion", {})
    ais_rules_corridor = combined_rules.get("shipping_corridor", {})
    ais_data = load_json(ROOT / "data" / "ais" / "latest.json")
    if ais_data:
        all_signals.extend(detect_port_activity_surge(ais_rules_activity, ais_data))
        all_signals.extend(detect_port_congestion(ais_rules_congestion, ais_data))
        all_signals.extend(detect_shipping_corridor(ais_rules_corridor, ais_data))

    # NHC storm risk
    nhc_rules = combined_rules.get("tropical_development", {})
    if nhc_data:
        all_signals.extend(detect_nhc_storm_risk(nhc_rules, nhc_data, noaa_alerts, ndbc_readings))

    # Delta detection
    state = load_state()
    current_ids = {s.id for s in all_signals}
    new_ids = {s.id for s in all_signals if s.id not in state}

    json_path, md_path = write_outputs(all_signals, data_dir, signal_dir)
    print(f"Wrote {json_path}", flush=True)
    print(f"Wrote {md_path}", flush=True)
    print(f"Composite signals: {len(all_signals)}", flush=True)
    print(f"New since last run: {len(new_ids)}", flush=True)

    save_state(current_ids)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-source signal merger for Abeng.")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--signal-dir", type=Path, default=DEFAULT_SIGNAL_DIR)
    args = parser.parse_args()
    return run(args.rules, args.data_dir, args.signal_dir)


if __name__ == "__main__":
    raise SystemExit(main())
