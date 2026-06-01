#!/usr/bin/env python3
"""Poll NOAA NWS API for active weather alerts in Caribbean zones.

Tracks alert IDs for delta detection. Emits signals only for new or
escalated alerts. Covers land-based alerts (PR/USVI) and marine zones
(Caribbean basin shipping lanes).

Outputs:
  data/noaa/latest.json  — full structured alert snapshot
  signals/noaa/latest.md — human-readable alert brief
"""

from __future__ import annotations

import argparse
import json
import logging
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "noaa_sources.json"
DEFAULT_DATA_DIR = ROOT / "data" / "noaa"
DEFAULT_SIGNAL_DIR = ROOT / "signals" / "noaa"
STATE_FILE = ROOT / "data" / "noaa" / ".sent_alerts.json"

USER_AGENT = "future-caribbean-signal-os/0.1"


@dataclass(frozen=True)
class WeatherAlert:
    id: str
    event: str
    headline: str
    severity: str
    urgency: str
    certainty: str
    area_desc: str
    sent: str
    effective: str
    expires: str
    description: str
    zone_type: str  # "land" or "marine"

    def fingerprint(self) -> str:
        return self.id


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_json(url: str, timeout: int) -> Any:
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


def extract_alerts(
    payload: Any, zone_type: str, exclude_events: list[str]
) -> list[WeatherAlert]:
    features = payload.get("features", [])
    alerts: list[WeatherAlert] = []
    for f in features:
        p = f.get("properties", {})
        event = p.get("event", "") or ""
        if exclude_events and event.lower() in [e.lower() for e in exclude_events]:
            continue
        alert = WeatherAlert(
            id=p.get("id", ""),
            event=event,
            headline=p.get("headline", "") or "",
            severity=p.get("severity", "Unknown"),
            urgency=p.get("urgency", "Unknown"),
            certainty=p.get("certainty", "Unknown"),
            area_desc=p.get("areaDesc", "") or "",
            sent=p.get("sent", "") or "",
            effective=p.get("effective", "") or "",
            expires=p.get("expires", "") or "",
            description=(p.get("description", "") or "")[:300],
            zone_type=zone_type,
        )
        alerts.append(alert)
    return alerts


def classify_severity(severity: str, priority_map: dict[str, int]) -> str:
    priority = priority_map.get(severity, 0)
    if priority >= 4:
        return "🔴 Critical"
    if priority >= 3:
        return "🟠 Severe"
    if priority >= 2:
        return "🟡 Moderate"
    return "🟢 Minor"


def format_alert_for_digest(alert: WeatherAlert, priority_map: dict[str, int]) -> str:
    icon = classify_severity(alert.severity, priority_map)
    zone_tag = "🌊" if alert.zone_type == "marine" else "🏝️"

    lines = [
        f"{icon} {zone_tag} **{alert.event}**",
        f"   Areas: {truncate(alert.area_desc, 120)}",
        f"   {alert.severity} · {alert.urgency} · {alert.certainty}",
    ]
    if alert.expires:
        try:
            expires_dt = datetime.fromisoformat(alert.expires.replace("Z", "+00:00"))
            expires_local = expires_dt.strftime("%b %d, %H:%M UTC")
            lines.append(f"   Expires: {expires_local}")
        except (ValueError, AttributeError):
            LOGGER.warning("NOAA observation parse error")
    return "\n".join(lines)


def truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def write_outputs(
    alerts: list[WeatherAlert],
    new_alerts: list[WeatherAlert],
    config: dict[str, Any],
    data_dir: Path,
    signal_dir: Path,
) -> tuple[Path, Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    signal_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()
    priority_map = config.get("severity_priority", {})

    payload = {
        "source": config["source"],
        "fetched_at": fetched_at,
        "total_active_alerts": len(alerts),
        "new_alerts": len(new_alerts),
        "alerts": [asdict(a) for a in alerts],
    }

    json_path = data_dir / "latest.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Build signal brief
    md_lines = [
        "# NOAA Caribbean Weather Alerts",
        "",
        f"- Source: {config['source']}",
        f"- Fetched: {fetched_at}",
        f"- Active alerts: {len(alerts)}",
        f"- New alerts since last check: {len(new_alerts)}",
        "",
    ]

    if new_alerts:
        md_lines.append("## New Weather Alerts")
        md_lines.append("")
        for a in sorted(
            new_alerts,
            key=lambda x: priority_map.get(x.severity, 0),
            reverse=True,
        ):
            md_lines.append(format_alert_for_digest(a, priority_map))
            md_lines.append("")

    # Current active alerts summary
    md_lines.append("## Active Alert Summary")
    md_lines.append("")
    by_type: dict[str, list[WeatherAlert]] = defaultdict(list)
    for a in alerts:
        by_type[a.event].append(a)

    for event, event_alerts in sorted(by_type.items()):
        highest = max(
            (priority_map.get(a.severity, 0) for a in event_alerts), default=0
        )
        worst = [s for s, p in priority_map.items() if p == highest][0]
        icon = classify_severity(worst, priority_map)
        total_areas = sum(len(a.area_desc.split(";")) for a in event_alerts)
        md_lines.append(f"{icon} **{event}** — {len(event_alerts)} zone(s), ~{total_areas} area(s)")
        expires = min(a.expires for a in event_alerts)
        if expires:
            try:
                e = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                md_lines.append(f"   Latest expiry: {e.strftime('%b %d, %H:%M UTC')}")
            except (ValueError, AttributeError):
                LOGGER.warning("NOAA data parse error")
            md_lines.append("")

    md_lines.append(f"**Total active alerts:** {len(alerts)}")
    md_lines.append(f"**New since last poll:** {len(new_alerts)}")

    md_path = signal_dir / "latest.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path


def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_state(alert_ids: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(alert_ids), indent=2) + "\n", encoding="utf-8")


def is_expired(alert: WeatherAlert) -> bool:
    if not alert.expires:
        return False
    try:
        expires_dt = datetime.fromisoformat(alert.expires.replace("Z", "+00:00"))
        return expires_dt < datetime.now(timezone.utc)
    except (ValueError, AttributeError):
        return False


def run(config_path: Path, data_dir: Path, signal_dir: Path, timeout: int) -> int:
    config = load_config(config_path)
    base = config["base_url"]
    exclude_events = config.get("exclude_events", [])

    all_alerts: list[WeatherAlert] = []
    errors: list[str] = []

    for area_code, area_config in config["areas"].items():
        url = f"{base}/alerts/active/area/{area_code}"
        try:
            payload = fetch_json(url, timeout)
            alerts = extract_alerts(payload, area_config["type"], exclude_events)
            all_alerts.extend(alerts)
        except Exception as exc:
            errors.append(f"{area_code}: {exc}")

    # Caribbean marine zones (NWS San Juan) — fetched by zone so we don't
    # pull US-mainland Atlantic waters. One request, comma-joined.
    mz = config.get("marine_zones") or {}
    zones = mz.get("zones", [])
    if zones:
        zone_q = ",".join(zones)
        url = f"{base}/alerts/active?zone={zone_q}"
        try:
            payload = fetch_json(url, timeout)
            alerts = extract_alerts(payload, mz.get("type", "marine"), exclude_events)
            all_alerts.extend(alerts)
        except Exception as exc:
            errors.append(f"marine_zones: {exc}")

    # Dedup by alert ID
    deduped: dict[str, WeatherAlert] = {}
    for a in all_alerts:
        deduped[a.id] = a
    alerts = list(deduped.values())

    if not alerts:
        print("No active alerts found.", file=sys.stderr)
        # Still write "all clear" output
        payload = {
            "source": config["source"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "total_active_alerts": 0,
            "new_alerts": 0,
            "alerts": [],
        }
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "latest.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return 0

    # Filter expired alerts
    active_alerts = [a for a in alerts if not is_expired(a)]

    # Delta detection
    state = load_state()
    current_ids = {a.fingerprint() for a in active_alerts}
    new = [a for a in active_alerts if a.fingerprint() not in state]

    # Update state with all current active alert IDs (remove expired ones)
    save_state(current_ids)

    json_path, md_path = write_outputs(
        active_alerts, new, config, data_dir, signal_dir
    )
    print(f"Wrote {json_path}", flush=True)
    print(f"Wrote {md_path}", flush=True)
    print(f"Active alerts: {len(active_alerts)}", flush=True)
    print(f"New alerts: {len(new)}", flush=True)
    if errors:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll NOAA NWS for Caribbean weather alerts.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--signal-dir", type=Path, default=DEFAULT_SIGNAL_DIR)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()
    return run(args.config, args.data_dir, args.signal_dir, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
