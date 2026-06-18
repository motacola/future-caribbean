#!/usr/bin/env python3
"""Poll AISstream.io for maritime vessel data in the Caribbean.

Collects vessel positions via WebSocket and computes:
- Port vessel density (congestion/activity)
- Shipping corridor traffic
- Anomalous vessel behavior
- Port dwell time estimates

Requires AISSTREAM_API_KEY environment variable (free from aisstream.io).
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import websockets

ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT / "config" / "ais_sources.json"
OUTPUT_FILE = ROOT / "data" / "ais" / "latest.json"

# Load config
with CONFIG_FILE.open() as f:
    CONFIG = json.load(f)

API_KEY = os.getenv("AISSTREAM_API_KEY")
WS_URL = CONFIG["base_url"]
BBOX = CONFIG["caribbean_bbox"]
PORTS = CONFIG["key_ports"]
MESSAGE_TYPES = CONFIG["message_types"]

# Collection window (seconds)
COLLECT_SECONDS = int(os.getenv("AIS_COLLECT_SECONDS", "120"))  # 2 min default


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two lat/lon points."""
    from math import radians, sin, cos, sqrt, asin
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


def vessel_near_port(lat: float, lon: float, port: dict) -> bool:
    """Check if vessel is within port radius."""
    return haversine(lat, lon, port["lat"], port["lon"]) <= port["bbox_radius_km"]


async def collect_ais_data(duration: int) -> dict:
    """Collect AIS data for specified duration via WebSocket."""
    if not API_KEY:
        return {"error": "AISSTREAM_API_KEY not set", "vessels": [], "ports": {}}

    subscription = {
        "APIKey": API_KEY,
        "BoundingBoxes": [[[BBOX["north"], BBOX["west"]], [BBOX["south"], BBOX["east"]]]],
        "FilterMessageTypes": MESSAGE_TYPES,
    }

    vessels: dict[str, dict] = {}  # MMSI -> latest data
    port_counts: dict[str, set] = defaultdict(set)  # port_name -> set of MMSIs
    message_count = 0

    try:
        async with websockets.connect(WS_URL, ping_interval=30, ping_timeout=10) as ws:
            await ws.send(json.dumps(subscription))

            start_time = time.time()
            while time.time() - start_time < duration:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(message)
                    message_count += 1

                    msg_type = data.get("MessageType")
                    ais = data.get("Message", {})
                    meta = data.get("MetaData", {})

                    if msg_type in ("PositionReport", "StandardClassBPositionReport"):
                        mmsi = str(ais.get("UserID") or ais.get("MMSI") or "")
                        if not mmsi:
                            continue

                        lat = ais.get("Latitude")
                        lon = ais.get("Longitude")
                        sog = ais.get("Sog")  # Speed over ground
                        cog = ais.get("Cog")  # Course over ground
                        true_heading = ais.get("TrueHeading")
                        nav_status = ais.get("NavStatus")

                        if lat is None or lon is None:
                            continue

                        # Check port proximity
                        near_ports = []
                        for port in PORTS:
                            if vessel_near_port(lat, lon, port):
                                near_ports.append(port["name"])
                                port_counts[port["name"]].add(mmsi)

                        vessels[mmsi] = {
                            "mmsi": mmsi,
                            "lat": lat,
                            "lon": lon,
                            "sog": sog,
                            "cog": cog,
                            "heading": true_heading,
                            "nav_status": nav_status,
                            "near_ports": near_ports,
                            "timestamp": meta.get("time_utc", datetime.now(timezone.utc).isoformat()),
                            "ship_name": meta.get("ShipName", ""),
                            "call_sign": meta.get("CallSign", ""),
                            "ship_type": meta.get("ShipType", ""),
                            "dimension": meta.get("Dimension", {}),
                        }

                    elif msg_type == "ShipStaticData":
                        mmsi = str(ais.get("UserID") or ais.get("MMSI") or "")
                        if mmsi and mmsi in vessels:
                            vessels[mmsi].update({
                                "ship_name": ais.get("ShipName", vessels[mmsi].get("ship_name", "")),
                                "call_sign": ais.get("CallSign", vessels[mmsi].get("call_sign", "")),
                                "ship_type": ais.get("ShipType", vessels[mmsi].get("ship_type", "")),
                                "destination": ais.get("Destination", ""),
                                "eta": ais.get("Eta", ""),
                                "draught": ais.get("Draught", 0),
                                "dimension": ais.get("Dimension", vessels[mmsi].get("dimension", {})),
                            })

                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception:
                    continue

    except Exception as e:
        return {"error": f"WebSocket error: {e}", "vessels": [], "ports": {}}

    # Build port summaries
    port_summaries = {}
    for port_name, mmsi_set in port_counts.items():
        port_vessels = [vessels[mmsi] for mmsi in mmsi_set if mmsi in vessels]
        port_summaries[port_name] = {
            "vessel_count": len(mmsi_set),
            "vessels": port_vessels[:20],  # Limit for output size
            "avg_sog": sum(v.get("sog", 0) for v in port_vessels if v.get("sog")) / max(1, len([v for v in port_vessels if v.get("sog")])),
        }

    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "collection_window_seconds": duration,
        "total_messages": message_count,
        "unique_vessels": len(vessels),
        "vessels": list(vessels.values()),
        "ports": port_summaries,
        "bbox": BBOX,
    }


def compute_port_signals(port_data: dict) -> list[dict]:
    """Compute signals from port activity data."""
    signals = []
    for port_name, data in port_data.items():
        count = data["vessel_count"]
        avg_sog = data.get("avg_sog", 0)

        # High activity signal
        if count >= 15:
            signals.append({
                "type": "high_port_activity",
                "port": port_name,
                "vessel_count": count,
                "avg_sog_kn": round(avg_sog, 1),
                "severity": "high" if count >= 30 else "medium",
            })

        # Congestion signal (vessels moving slowly near port)
        slow_vessels = sum(1 for v in data.get("vessels", []) if v.get("sog", 99) < 3 and v.get("sog", 0) > 0)
        if slow_vessels >= 5:
            signals.append({
                "type": "port_congestion",
                "port": port_name,
                "slow_vessels": slow_vessels,
                "avg_sog_kn": round(avg_sog, 1),
            })

    return signals


def compute_corridor_signals(vessels: list[dict]) -> list[dict]:
    """Detect shipping corridor patterns from vessel positions."""
    # Simple clustering by latitude bands
    bands = defaultdict(list)
    for v in vessels:
        lat = v.get("lat", 0)
        band = round(lat / 2) * 2  # 2-degree latitude bands
        bands[band].append(v)

    signals = []
    for band, band_vessels in bands.items():
        if len(band_vessels) >= 20:
            # Check if vessels are moving in similar direction (corridor)
            courses = [v.get("cog", 0) for v in band_vessels if v.get("cog") is not None]
            if courses:
                avg_course = sum(courses) / len(courses)
                # Eastbound (~90) or Westbound (~270) traffic
                if 45 <= avg_course <= 135:
                    direction = "eastbound"
                elif 225 <= avg_course <= 315:
                    direction = "westbound"
                else:
                    direction = "mixed"

                signals.append({
                    "type": "shipping_corridor",
                    "lat_band": band,
                    "vessel_count": len(band_vessels),
                    "avg_course": round(avg_course, 1),
                    "direction": direction,
                })

    return signals


def main() -> int:
    print(f"[AIS Watcher] Starting collection for {COLLECT_SECONDS}s...", flush=True)

    # Run async collection
    try:
        data = asyncio.run(collect_ais_data(COLLECT_SECONDS))
    except RuntimeError:
        # Handle case where event loop already running
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(collect_ais_data(COLLECT_SECONDS))

    if "error" in data:
        print(f"[AIS Watcher] Error: {data['error']}", flush=True)
        # Write empty but valid structure
        data = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "error": data["error"],
            "collection_window_seconds": COLLECT_SECONDS,
            "total_messages": 0,
            "unique_vessels": 0,
            "vessels": [],
            "ports": {},
            "signals": [],
            "corridors": [],
        }
    else:
        # Add computed signals
        data["signals"] = compute_port_signals(data.get("ports", {}))
        data["corridors"] = compute_corridor_signals(data.get("vessels", []))
        data["fetched_at"] = datetime.now(timezone.utc).isoformat()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"[AIS Watcher] Wrote {OUTPUT_FILE}", flush=True)
    print(f"  Vessels: {data.get('unique_vessels', 0)}", flush=True)
    print(f"  Messages: {data.get('total_messages', 0)}", flush=True)
    print(f"  Port signals: {len(data.get('signals', []))}", flush=True)
    print(f"  Corridor signals: {len(data.get('corridors', []))}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())