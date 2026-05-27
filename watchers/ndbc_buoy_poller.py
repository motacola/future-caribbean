#!/usr/bin/env python3
"""Poll NOAA NDBC buoys for real-time Caribbean marine conditions.

Tracks 6 buoys across eastern, northern, and western Caribbean.
Data is tab-delimited text, updated every 10 minutes. Maintains a
rolling history for pressure-trend detection.

Outputs:
  data/ndbc/latest.json  — full structured snapshot per buoy
  data/ndbc/history.json — rolling 3-hour pressure history for trend detection
  signals/ndbc/latest.md — human-readable marine conditions brief
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "ndbc_sources.json"
DEFAULT_DATA_DIR = ROOT / "data" / "ndbc"
DEFAULT_SIGNAL_DIR = ROOT / "signals" / "ndbc"
HISTORY_FILE = ROOT / "data" / "ndbc" / "history.json"
STATE_FILE = ROOT / "data" / "ndbc" / ".sent_signals.json"

USER_AGENT = "future-caribbean-signal-os/0.1"
MS_TO_KNOTS = 1.94384
HPA_FLOAT_FIELDS = {"PRES"}


@dataclass(frozen=True)
class BuoyReading:
    station_id: str
    station_name: str
    region: str
    timestamp: str  # ISO format
    wind_dir_deg: float | None
    wind_speed_ms: float | None
    wind_gust_ms: float | None
    wave_height_m: float | None
    wave_period_s: float | None
    pressure_hpa: float | None
    air_temp_c: float | None
    water_temp_c: float | None

    def wind_speed_kts(self) -> float | None:
        if self.wind_speed_ms is None:
            return None
        return round(self.wind_speed_ms * MS_TO_KNOTS, 1)

    def wind_gust_kts(self) -> float | None:
        if self.wind_gust_ms is None:
            return None
        return round(self.wind_gust_ms * MS_TO_KNOTS, 1)


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_text(url: str, timeout: int) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                return resp.read().decode("utf-8")
        raise


def parse_buoy_data(text: str) -> list[dict[str, Any]]:
    """Parse NDBC tabular format into list of row dicts."""
    lines = text.strip().splitlines()
    if not lines:
        return []

    # Find header and data lines
    header_line = None
    data_lines = []
    for i, line in enumerate(lines):
        if line.startswith("#YY"):
            header_line = line
            # NDBC uses two header rows: #YY... (names) then #yr... (units)
            skip = 2
            data_lines = lines[i + skip:]
            break

    if header_line is None:
        return []

    # Parse header — strip # and split by whitespace
    headers = header_line.lstrip("#").strip().split()
    rows = []
    for line in data_lines:
        parts = line.strip().split()
        if len(parts) < len(headers):
            continue
        row = {}
        for j, hdr in enumerate(headers):
            val = parts[j] if j < len(parts) else "MM"
            row[hdr] = val
        rows.append(row)

    return rows


def row_to_reading(
    row: dict[str, Any],
    station_id: str,
    station_name: str,
    region: str,
) -> BuoyReading:
    def to_float(key: str) -> float | None:
        v = row.get(key, "MM")
        if v in ("MM", "999.0", "99.00", "999"):
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    year = row.get("YY", "2026")
    # NDBC uses MM for month AND for missing values — handle via position
    # Actual header order: YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS PTDY TIDE
    parts = list(row.values())
    month_val = parts[1] if len(parts) > 1 else "01"
    day_val = parts[2] if len(parts) > 2 else "01"
    hour_val = parts[3] if len(parts) > 3 else "00"
    min_val = parts[4] if len(parts) > 4 else "00"

    try:
        ts = datetime(
            int(year),
            int(month_val),
            int(day_val),
            int(hour_val),
            int(min_val),
            tzinfo=timezone.utc,
        )
    except (ValueError, IndexError):
        ts = datetime.now(timezone.utc)

    return BuoyReading(
        station_id=station_id,
        station_name=station_name,
        region=region,
        timestamp=ts.isoformat(),
        wind_dir_deg=to_float("WDIR"),
        wind_speed_ms=to_float("WSPD"),
        wind_gust_ms=to_float("GST"),
        wave_height_m=to_float("WVHT"),
        wave_period_s=to_float("DPD"),
        pressure_hpa=to_float("PRES"),
        air_temp_c=to_float("ATMP"),
        water_temp_c=to_float("WTMP"),
    )


def load_history() -> dict[str, list[dict]]:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {}


def save_history(history: dict[str, list[dict]]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Prune history entries older than 4 hours
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
    pruned: dict[str, list[dict]] = {}
    for sid, entries in history.items():
        pruned[sid] = [e for e in entries if e.get("timestamp", "") > cutoff]
    HISTORY_FILE.write_text(json.dumps(pruned, indent=2) + "\n", encoding="utf-8")


def detect_signals(
    reading: BuoyReading,
    history_entries: list[dict],
    thresholds: dict[str, Any],
) -> list[str]:
    signals: list[str] = []
    s = reading.station_name
    wind_kts = reading.wind_speed_kts()
    gust_kts = reading.wind_gust_kts()

    if wind_kts is not None and wind_kts >= thresholds.get("wind_high_kts", 28):
        signals.append(
            f"🌬️ **High wind** at {s}: {wind_kts:.0f} kts "
            f"(gust {gust_kts:.0f} kts)" if gust_kts else f"🌬️ **High wind** at {s}: {wind_kts:.0f} kts"
        )

    if gust_kts is not None and gust_kts >= thresholds.get("wind_gust_high_kts", 34):
        signals.append(
            f"💨 **Strong gusts** at {s}: {gust_kts:.0f} kts"
        )

    if wind_kts is not None and wind_kts <= thresholds.get("wind_low_kts", 3):
        signals.append(
            f"🍃 **Light wind** at {s}: {wind_kts:.0f} kts"
        )

    if reading.wave_height_m is not None and reading.wave_height_m >= thresholds.get("wave_height_high_m", 3.0):
        signals.append(
            f"🌊 **High seas** at {s}: {reading.wave_height_m:.1f}m"
        )

    if reading.pressure_hpa is not None:
        if reading.pressure_hpa <= thresholds.get("pressure_very_low_hpa", 1005):
            signals.append(
                f"⚠️ **Very low pressure** at {s}: {reading.pressure_hpa:.1f} hPa"
            )

        # Pressure trend from history
        if len(history_entries) >= 2:
            # Sort by timestamp
            sorted_entries = sorted(history_entries, key=lambda e: e.get("timestamp", ""))
            oldest = None
            for entry in sorted_entries:
                p = entry.get("pressure_hpa")
                if p is not None:
                    oldest = p
                    break
            if oldest is not None and sorted_entries[-1].get("pressure_hpa") is not None:
                newest = sorted_entries[-1]["pressure_hpa"]
                drop = oldest - newest
                if drop >= thresholds.get("pressure_drop_3h_hpa", 3.0):
                    signals.append(
                        f"📉 **Pressure dropping** at {s}: -{drop:.1f} hPa in ~{min(len(sorted_entries), 18)} readings"
                    )

    return signals


def write_outputs(
    readings: list[BuoyReading],
    signals: list[str],
    config: dict[str, Any],
    data_dir: Path,
    signal_dir: Path,
) -> tuple[Path, Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    signal_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "source": config["source"],
        "fetched_at": fetched_at,
        "buoys": len(readings),
        "signals": len(signals),
        "readings": [asdict(r) for r in readings],
        "signals_list": signals,
    }

    json_path = data_dir / "latest.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def fmt_wind(r: BuoyReading) -> str:
        kts = r.wind_speed_kts()
        gust = r.wind_gust_kts()
        if kts is None:
            return "—"
        parts = [f"{kts:.0f} kts"]
        if gust is not None:
            parts.append(f"gust {gust:.0f}")
        dir_str = f" from {r.wind_dir_deg:.0f}°" if r.wind_dir_deg is not None else ""
        return ", ".join(parts) + dir_str

    md_lines = [
        "# NDBC Caribbean Buoy Conditions",
        "",
        f"- Source: {config['source']}",
        f"- Fetched: {fetched_at}",
        f"- Buoys reporting: {len(readings)}",
        "",
    ]

    if signals:
        md_lines.extend([
            "## Marine Signals",
            "",
        ])
        for s in signals:
            md_lines.append(f"- {s}")
        md_lines.append("")

    md_lines.append("## Current Conditions")
    md_lines.append("")
    for r in sorted(readings, key=lambda x: x.region):
        wind = fmt_wind(r)
        wave = f"{r.wave_height_m:.1f}m" if r.wave_height_m is not None else "—"
        press = f"{r.pressure_hpa:.1f} hPa" if r.pressure_hpa is not None else "—"
        water = f"{r.water_temp_c:.1f}°C" if r.water_temp_c is not None else "—"
        region_icon = {"eastern": "🌅", "northern": "⬆️", "western": "🌅"}.get(r.region, "🌊")

        md_lines.append(f"**{r.station_name}** {region_icon}")
        md_lines.append(f"  🌬️ {wind}")
        md_lines.append(f"  🌊 Wave: {wave}")
        md_lines.append(f"  📊 Pressure: {press}")
        md_lines.append(f"  🌡️ Water: {water}")
        md_lines.append("")

    md_lines.append(f"**Buoys reporting:** {len(readings)}")
    md_lines.append(f"**Active marine signals:** {len(signals)}")

    md_path = signal_dir / "latest.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path


def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_state(fingerprints: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(fingerprints), indent=2) + "\n", encoding="utf-8")


def fingerprint(reading: BuoyReading, signals: list[str]) -> str:
    """Fingerprint = station + timestamp + signal hashes."""
    signal_hash = hash(tuple(sorted(signals))) % 100000 if signals else 0
    return f"{reading.station_id}@{reading.timestamp[:16]}:{signal_hash}"


def run(
    config_path: Path,
    data_dir: Path,
    signal_dir: Path,
    timeout: int,
) -> int:
    config = load_config(config_path)
    base = config["base_url"]
    buoys = config["buoys"]
    thresholds = config.get("signal_thresholds", {})
    history = load_history()

    readings: list[BuoyReading] = []
    errors: list[str] = []

    for sid, info in buoys.items():
        url = f"{base}/{sid}.txt"
        try:
            text = fetch_text(url, timeout)
            rows = parse_buoy_data(text)
            if rows:
                reading = row_to_reading(rows[0], sid, info["name"], info["region"])
                readings.append(reading)

                # Update history
                if reading.pressure_hpa is not None:
                    if sid not in history:
                        history[sid] = []
                    history[sid].append({
                        "timestamp": reading.timestamp,
                        "pressure_hpa": reading.pressure_hpa,
                        "wind_speed_ms": reading.wind_speed_ms,
                    })
        except Exception as exc:
            errors.append(f"{sid} ({info['name']}): {exc}")

    save_history(history)

    if not readings:
        print("No buoy readings obtained.", file=sys.stderr)
        return 1

    # Detect signals
    all_signals: list[str] = []
    for r in readings:
        station_history = history.get(r.station_id, [])
        sigs = detect_signals(r, station_history, thresholds)
        all_signals.extend(sigs)

    # Delta detection
    state = load_state()
    current_fps = {fingerprint(r, all_signals) for r in readings}
    new_signals = [s for s in all_signals if fingerprint(readings[0], all_signals) not in state]

    json_path, md_path = write_outputs(readings, all_signals, config, data_dir, signal_dir)
    print(f"Wrote {json_path}", flush=True)
    print(f"Wrote {md_path}", flush=True)
    print(f"Buoys: {len(readings)}", flush=True)
    print(f"Signals: {len(all_signals)}", flush=True)
    print(f"New since last poll: {len(new_signals)}", flush=True)

    if errors:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)

    save_state(current_fps)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll NDBC buoys for Caribbean marine conditions.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--signal-dir", type=Path, default=DEFAULT_SIGNAL_DIR)
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()
    return run(args.config, args.data_dir, args.signal_dir, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
