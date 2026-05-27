#!/usr/bin/env python3
"""Poll NHC for Atlantic tropical cyclone outlook and active storms.

Uses the NWS API for TWO (Tropical Weather Outlook) products to track
development areas, and TCP/TCM products for active storm tracking.

Hurricane season runs June 1–November 30. During off-season, TWO
products say "formation not expected." The watcher still runs and
will detect the first disturbance automatically.

Outputs:
  data/nhc/latest.json  — structured outlook + active storm data
  signals/nhc/latest.md — human-readable storm/intel brief
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import logging

LOGGER = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "nhc"
DEFAULT_SIGNAL_DIR = ROOT / "signals" / "nhc"
STATE_FILE = ROOT / "data" / "nhc" / ".sent_outlook.json"

USER_AGENT = "future-caribbean-signal-os/0.1"
NWS_API = "https://api.weather.gov"
ATLANTIC_TWO_COLLECTIVE = "ABNT20"  # Atlantic Tropical Weather Outlook

# Probability thresholds for TWO products
PROB_KEYWORDS = {
    "low": r"(?:low|less than 40).*percent",
    "medium": r"(?:medium|near 40 to 60|40.*percent).*percent",
    "high": r"(?:high|greater than 60|70.*percent).*percent",
}


@dataclass(frozen=True)
class DevelopmentArea:
    label: str
    probability: str  # "low", "medium", "high"
    location: str
    description: str
    days: int  # 2 or 7


@dataclass(frozen=True)
class ActiveStorm:
    name: str
    basin: str
    storm_type: str  # "Tropical Depression", "Tropical Storm", "Hurricane", etc.
    wind_kts: int | None
    pressure_mb: int | None
    lat: float | None
    lon: float | None
    movement: str
    forecast: str


@dataclass(frozen=True)
class NhcSnapshot:
    issuance_time: str
    outlook_text: str
    development_areas: list[dict]
    active_storms: list[dict]
    summary: str


# ── NWS API helpers ────────────────────────────────────────


def nws_fetch(path: str, timeout: int = 15) -> Any:
    url = f"{NWS_API}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                return json.loads(resp.read().decode("utf-8"))
        raise


def fetch_product_text(product_id: str) -> str | None:
    """Fetch a single NWS product by ID and return its text content."""
    try:
        data = nws_fetch(f"/products/{product_id}")
        return data.get("productText", "")
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return None


def find_latest_tropical_products(
    product_code: str, wmo_collective: str, limit: int = 5
) -> list[dict]:
    """Find the latest NWS products by code + WMO collective ID (e.g. ABNT20)."""
    try:
        data = nws_fetch(f"/products/types/{product_code}")
        items = data.get("@graph", [])
        return [
            item
            for item in items
            if item.get("wmoCollectiveId", "") == wmo_collective
        ][:limit]
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return []


# ── TWO parser ─────────────────────────────────────────────


def parse_two_text(text: str) -> tuple[list[DevelopmentArea], str]:
    """Parse Atlantic TWO product text for development areas.

    Returns (areas, summary_line).
    Off-season: empty areas, "formation not expected" summary.
    Active season: up to several areas with location/probability.
    """
    areas: list[DevelopmentArea] = []
    summary = "Tropical cyclone formation is not expected during the next 7 days."

    # Find the basin-specific section
    # TWO text has format:
    # For the North Atlantic...Caribbean Sea and the Gulf of America:
    # <blank line>
    # <description paragraphs>
    # $$
    # Forecaster Name

    lines = text.splitlines()
    in_caribbean_section = False
    current_area_lines: list[str] = []
    collecting_area = False

    for line in lines:
        stripped = line.strip()

        # Detect the Atlantic/Caribbean section
        if "North Atlantic" in stripped or "Caribbean Sea" in stripped:
            in_caribbean_section = True
            continue

        if not in_caribbean_section:
            continue

        # End of outlook
        if stripped.startswith("$$") or stripped.startswith("Forecaster"):
            break

        # Check for development area markers
        # Format: "1. Near the ..."
        # Or: "An area of ..."
        if re.match(r"^\d+\.\s", stripped) or stripped.startswith("An area"):
            # Save any previous area
            if current_area_lines and collecting_area:
                _parse_and_add_area(current_area_lines, areas)

            current_area_lines = [stripped]
            collecting_area = True
        elif collecting_area and stripped:
            current_area_lines.append(stripped)

        # Check for "formation is not expected" or "formation expected"
        if "formation" in stripped.lower() and "expect" in stripped.lower():
            summary = stripped

    # Don't forget the last area
    if current_area_lines and collecting_area:
        _parse_and_add_area(current_area_lines, areas)

    return areas, summary


def _parse_and_add_area(lines: list[str], areas: list[DevelopmentArea]):
    """Parse accumulated lines into a DevelopmentArea."""
    full_text = " ".join(lines)
    label = lines[0] if lines else "Unknown area"

    # Determine probability
    probability = "low"
    for prob, pattern in PROB_KEYWORDS.items():
        if re.search(pattern, full_text, re.IGNORECASE):
            probability = prob
            break

    # Determine days (2-day vs 7-day)
    days = 7
    if re.search(r"(?:next 2|48 hours|2-day)", full_text, re.IGNORECASE):
        days = 2

    # Extract location hints
    location = ""
    loc_patterns = [
        r"(?:near|off|over|east|west|north|south|about)\s+(\d+\s*(?:N|S|degrees)?.*?)(?=\.|\,)",
        r"(?:Caribbean|Atlantic|Gulf|Bahamas|Lesser Antilles|Greater Antilles|Windward|Leeward)",
    ]
    for pat in loc_patterns:
        m = re.search(pat, full_text, re.IGNORECASE)
        if m:
            location = m.group(0) if m.groups() else m.group(0)
            break

    description = full_text[:300] if len(full_text) > 300 else full_text

    areas.append(
        DevelopmentArea(
            label=label[:120],
            probability=probability,
            location=location or "Caribbean/Atlantic basin",
            description=description,
            days=days,
        )
    )


def format_summary(areas: list[DevelopmentArea], default_summary: str) -> str:
    """Generate a human-readable summary."""
    if not areas:
        return default_summary

    parts = []
    probs = {"high": [], "medium": [], "low": []}
    for area in areas:
        probs[area.probability].append(area)

    if probs["high"]:
        parts.append(
            f"{len(probs['high'])} {'high-probability' if len(probs['high']) > 1 else 'high'} development area(s)"
        )
    if probs["medium"]:
        parts.append(
            f"{len(probs['medium'])} {'medium-probability' if len(probs['medium']) > 1 else 'medium'} area(s)"
        )
    if probs["low"] and not parts:
        parts.append(
            f"{len(probs['low'])} low-probability area(s) being monitored"
        )

    if parts:
        return f"Atlantic tropical outlook: {', '.join(parts)}."
    return default_summary


# ── Active storm detection ──────────────────────────────────


def check_active_storms() -> list[ActiveStorm]:
    """Check for active tropical cyclone products (TCP = Public Advisory).

    Returns empty list off-season. Returns storm data when active.
    """
    storms: list[ActiveStorm] = []
    try:
        products = nws_fetch("/products/types/TCP")
        items = products.get("@graph", [])
        # Get the latest Atlantic TCP (TC PAT)
        atlantic_tcps = [
            item
            for item in items
            if item.get("wmoCollectiveId", "").startswith("TC")
        ]
        if not atlantic_tcps:
            return storms

        # Get the most recent
        latest = max(
            atlantic_tcps,
            key=lambda x: x.get("issuanceTime", ""),
        )
        text = fetch_product_text(latest.get("id", ""))
        if not text:
            return storms

        # Parse basic storm info from TCP text
        # Format: "...HURRICANE BERYL...OR...TROPICAL STORM ALBERTO..."
        storm_name = ""
        storm_type = "Tropical Cyclone"
        name_match = re.search(
            r"(?:HURRICANE|TROPICAL STORM|TROPICAL DEPRESSION)\s+([A-Z]+)",
            text,
        )
        if name_match:
            type_raw = name_match.group(0)
            if "HURRICANE" in type_raw:
                storm_type = "Hurricane"
            elif "TROPICAL STORM" in type_raw:
                storm_type = "Tropical Storm"
            elif "TROPICAL DEPRESSION" in type_raw:
                storm_type = "Tropical Depression"
            storm_name = name_match.group(1).title()

        # Extract position
        pos_match = re.search(
            r"(?:NEAR|CENTER LOCATED)\s*(?:LATITUDE\s*)?(\d+\.?\d*)\s*(N|S)\s*(?:LONGITUDE\s*)?(\d+\.?\d*)\s*(W|E)",
            text,
            re.IGNORECASE,
        )
        lat = float(pos_match.group(1)) if pos_match else None
        lon = float(pos_match.group(3)) if pos_match else None

        # Extract wind
        wind_match = re.search(
            r"(?:MAXIMUM SUSTAINED WINDS?\s*|WINDS?\s*NEAR\s*)(\d+)\s*(?:KT|MPH|KM/H)",
            text,
            re.IGNORECASE,
        )
        wind_kts = int(wind_match.group(1)) if wind_match else None

        # Extract pressure
        press_match = re.search(
            r"(?:MINIMUM CENTRAL PRESSURE\s*|PRESSURE\s*)(\d+)\s*MB",
            text,
            re.IGNORECASE,
        )
        pressure = int(press_match.group(1)) if press_match else None

        storms.append(
            ActiveStorm(
                name=storm_name or "Unnamed",
                basin="Atlantic",
                storm_type=storm_type,
                wind_kts=wind_kts,
                pressure_mb=pressure,
                lat=lat,
                lon=lon,
                movement="",
                forecast="",
            )
        )

    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        LOGGER.warning("NHC storm fetch failed")
        pass

    return storms


# ── Delta tracking ─────────────────────────────────────────


def load_state(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            LOGGER.warning("NHC storm file read error")
    return {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


# ── Output writers ─────────────────────────────────────────


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_signal_md(snapshot: NhcSnapshot, path: Path) -> None:
    """Write human-readable storm intel brief."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NHC Storm Intelligence",
        "",
        f"Issued: {snapshot.issuance_time}",
        f"Summary: {snapshot.summary}",
        "",
    ]

    if snapshot.development_areas:
        lines.append("## Development Areas")
        lines.append("")
        for area in snapshot.development_areas:
            prob_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            lines.append(
                f"- {prob_icon.get(area['probability'], '⚪')} [{area['probability'].upper()}] {area['label']}"
            )
            if area.get("location"):
                lines.append(f"  Location: {area['location']}")
            lines.append("")
    else:
        lines.append("No active development areas.")
        lines.append("")

    if snapshot.active_storms:
        lines.append("## Active Storms")
        lines.append("")
        for storm in snapshot.active_storms:
            lines.append(f"- **{storm['name']}** ({storm['storm_type']})")
            if storm.get("wind_kts"):
                lines.append(f"  Winds: {storm['wind_kts']} kt")
            if storm.get("pressure_mb"):
                lines.append(f"  Pressure: {storm['pressure_mb']} mb")
            if storm.get("lat") and storm.get("lon"):
                lines.append(f"  Position: {storm['lat']}N {storm['lon']}W")
            lines.append("")

    lines.append("---")
    lines.append("Source: NWS National Hurricane Center (NHC)")
    lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


# ── Main ────────────────────────────────────────────────────


def run(data_dir: Path, signal_dir: Path) -> int:
    state = load_state(STATE_FILE)
    last_product_id = state.get("last_product_id", "")

    # 1. Fetch latest Atlantic TWO
    two_items = find_latest_tropical_products("TWO", ATLANTIC_TWO_COLLECTIVE, limit=1)
    if not two_items:
        print("NHC: Could not fetch Atlantic TWO product (offline or off-season).")
        return 1

    latest = two_items[0]
    product_id = latest.get("id", "")
    issuance_time = latest.get("issuanceTime", "")

    text = fetch_product_text(product_id)
    if not text:
        print("NHC: Could not fetch TWO product text.")
        return 1

    # 2. Parse development areas
    areas, default_summary = parse_two_text(text)
    summary = format_summary(areas, default_summary)

    # 3. Check for active storms
    active_storms = check_active_storms()

    is_new = product_id != last_product_id
    has_active_storms = bool(active_storms)
    has_development = bool(areas)

    # 4. Build snapshot
    snapshot = NhcSnapshot(
        issuance_time=issuance_time,
        outlook_text=text,
        development_areas=[asdict(a) for a in areas],
        active_storms=[asdict(s) for s in active_storms],
        summary=summary,
    )

    # 5. Write structured data
    write_json({"product_id": product_id, "issuance_time": issuance_time, "snapshot": asdict(snapshot)}, data_dir / "latest.json")

    # 6. Write signal
    write_signal_md(snapshot, signal_dir / "latest.md")

    # 7. Output summary for delta tracking / cron delivery
    if is_new and (has_development or has_active_storms):
        print(f"🌪️ NHC: {summary}")
        for area in areas:
            prob_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            print(f"   {prob_icon.get(area.probability, '⚪')} {area.label}")
        for storm in active_storms:
            print(f"   🌀 {storm.storm_type} {storm.name}")
        save_state(STATE_FILE, {"last_product_id": product_id})
    elif is_new and not has_development and not has_active_storms:
        # Off-season — still save state but output nothing (no signal to deliver)
        save_state(STATE_FILE, {"last_product_id": product_id})
    else:
        # Same product — no output (no new signal)
        pass

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="NHC Storm Intelligence Watcher.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--signal-dir", type=Path, default=DEFAULT_SIGNAL_DIR)
    args = parser.parse_args()

    return run(args.data_dir, args.signal_dir)


if __name__ == "__main__":
    raise SystemExit(main())
