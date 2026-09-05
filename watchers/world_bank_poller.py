#!/usr/bin/env python3
"""Poll World Bank public indicators and emit Caribbean signal briefs.

No API key is required. The script is intentionally stdlib-only so it can run
from cron/launchd without a project virtualenv.
"""

from __future__ import annotations

import argparse
import json
import math
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "world_bank_indicators.json"
DEFAULT_DATA_DIR = ROOT / "data" / "world_bank"
DEFAULT_SIGNAL_DIR = ROOT / "signals" / "world_bank"
WORLD_BANK_BASE = "https://api.worldbank.org/v2"


@dataclass(frozen=True)
class Observation:
    country_code: str
    country_name: str
    indicator_code: str
    indicator_label: str
    year: int
    value: float
    previous_year: int | None
    previous_value: float | None
    delta: float | None
    delta_pct: float | None


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_json(url: str, timeout: int) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "future-caribbean-signal-os/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
                return json.loads(response.read().decode("utf-8"))
        raise


def world_bank_indicator_url(country: str, indicator: str, per_page: int) -> str:
    query = urllib.parse.urlencode({"format": "json", "per_page": per_page})
    return f"{WORLD_BANK_BASE}/country/{country}/indicator/{indicator}?{query}"


def numeric_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        return []
    rows = []
    for row in payload[1]:
        if row.get("value") is None:
            continue
        try:
            year = int(row["date"])
            value = float(row["value"])
        except (KeyError, TypeError, ValueError):
            continue
        rows.append({"year": year, "value": value})
    return sorted(rows, key=lambda item: item["year"], reverse=True)


def latest_observation(
    country_code: str,
    country_name: str,
    indicator_code: str,
    indicator_label: str,
    rows: list[dict[str, Any]],
) -> Observation | None:
    if not rows:
        return None
    latest = rows[0]
    previous = rows[1] if len(rows) > 1 else None
    delta = None
    delta_pct = None
    previous_year = None
    previous_value = None
    if previous:
        previous_year = int(previous["year"])
        previous_value = float(previous["value"])
        delta = latest["value"] - previous_value
        if previous_value != 0:
            delta_pct = (delta / abs(previous_value)) * 100
    return Observation(
        country_code=country_code,
        country_name=country_name,
        indicator_code=indicator_code,
        indicator_label=indicator_label,
        year=int(latest["year"]),
        value=float(latest["value"]),
        previous_year=previous_year,
        previous_value=previous_value,
        delta=delta,
        delta_pct=delta_pct,
    )


def format_value(value: float, kind: str) -> str:
    if kind == "currency":
        if abs(value) >= 1_000_000_000:
            return f"USD {value / 1_000_000_000:.2f}B"
        if abs(value) >= 1_000_000:
            return f"USD {value / 1_000_000:.2f}M"
        return f"USD {value:,.0f}"
    if kind == "percent":
        return f"{value:.2f}%"
    if kind == "count":
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def signal_for(obs: Observation, indicator_cfg: dict[str, Any]) -> str | None:
    kind = indicator_cfg.get("kind", "number")
    abs_threshold = indicator_cfg.get("signal_threshold_abs")
    pct_threshold = indicator_cfg.get("signal_threshold_pct")

    if abs_threshold is not None and abs(obs.value) >= float(abs_threshold):
        return f"{obs.country_name}: {obs.indicator_label} is {format_value(obs.value, kind)} ({obs.year})."

    if pct_threshold is not None and obs.delta_pct is not None and abs(obs.delta_pct) >= float(pct_threshold):
        direction = "up" if obs.delta_pct > 0 else "down"
        return (
            f"{obs.country_name}: {obs.indicator_label} moved {direction} "
            f"{abs(obs.delta_pct):.1f}% from {obs.previous_year} to {obs.year}."
        )

    return None


def serialize_observation(obs: Observation) -> dict[str, Any]:
    return {
        "country_code": obs.country_code,
        "country_name": obs.country_name,
        "indicator_code": obs.indicator_code,
        "indicator_label": obs.indicator_label,
        "year": obs.year,
        "value": obs.value,
        "previous_year": obs.previous_year,
        "previous_value": obs.previous_value,
        "delta": obs.delta,
        "delta_pct": obs.delta_pct,
    }


def fetch_observation(
    country_code: str,
    country_name: str,
    indicator_code: str,
    indicator_cfg: dict[str, Any],
    timeout: int,
    per_page: int,
) -> tuple[Observation | None, str | None]:
    url = world_bank_indicator_url(country_code, indicator_code, per_page)
    try:
        rows = numeric_rows(fetch_json(url, timeout))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, f"{country_code}/{indicator_code}: {exc}"
    obs = latest_observation(
        country_code,
        country_name,
        indicator_code,
        indicator_cfg["label"],
        rows,
    )
    return obs, None


def write_outputs(
    observations: list[Observation],
    signals: list[str],
    config: dict[str, Any],
    data_dir: Path,
    signal_dir: Path,
    errors: list[str] | None = None,
) -> tuple[Path, Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    signal_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()

    # A run where every request failed must not look like a healthy refresh.
    # Record the outcome next to the timestamp so freshness checks
    # (packagers/source_health.py, /api/status) can tell a real collection
    # from an empty one that merely reset the clock.
    payload = {
        "source": "World Bank API",
        "fetched_at": fetched_at,
        "ok": bool(observations),
        "errors": list(errors or []),
        "countries": config["countries"],
        "indicators": config["indicators"],
        "observations": [serialize_observation(obs) for obs in observations],
        "signals": signals,
    }

    json_path = data_dir / "latest.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md_lines = [
        "# World Bank Caribbean Signals",
        "",
        "- Source: World Bank API",
        f"- Fetched: {fetched_at}",
        f"- Countries: {len(config['countries'])}",
        f"- Indicators: {len(config['indicators'])}",
        "",
        "## Signals",
        "",
    ]
    if signals:
        md_lines.extend(f"- {signal}" for signal in signals)
    else:
        md_lines.append("- No threshold signals found in this run.")

    md_lines.extend(["", "## Latest Observations", ""])
    for obs in sorted(observations, key=lambda item: (item.indicator_label, item.country_name)):
        kind = config["indicators"][obs.indicator_code].get("kind", "number")
        value = format_value(obs.value, kind)
        if obs.delta_pct is not None and math.isfinite(obs.delta_pct):
            change = f", {obs.delta_pct:+.1f}% vs {obs.previous_year}"
        else:
            change = ""
        md_lines.append(f"- {obs.country_name} - {obs.indicator_label}: {value} ({obs.year}{change})")

    md_path = signal_dir / "latest.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path


def run(config_path: Path, data_dir: Path, signal_dir: Path, timeout: int, per_page: int) -> int:
    config = load_config(config_path)
    observations: list[Observation] = []
    errors: list[str] = []
    jobs = [
        (country_code, country_name, indicator_code, indicator_cfg)
        for country_code, country_name in config["countries"].items()
        for indicator_code, indicator_cfg in config["indicators"].items()
    ]

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(
                fetch_observation,
                country_code,
                country_name,
                indicator_code,
                indicator_cfg,
                timeout,
                per_page,
            )
            for country_code, country_name, indicator_code, indicator_cfg in jobs
        ]
        for future in as_completed(futures):
            obs, error = future.result()
            if obs:
                observations.append(obs)
            if error:
                errors.append(error)

    signals = []
    for obs in observations:
        signal = signal_for(obs, config["indicators"][obs.indicator_code])
        if signal:
            signals.append(signal)

    json_path, md_path = write_outputs(observations, signals, config, data_dir, signal_dir, errors)
    print(f"Wrote {json_path}", flush=True)
    print(f"Wrote {md_path}", flush=True)
    print(f"Observations: {len(observations)}", flush=True)
    print(f"Signals: {len(signals)}", flush=True)
    if errors:
        print("Errors:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
    return 0 if observations else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll World Bank indicators for Caribbean signals.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--signal-dir", type=Path, default=DEFAULT_SIGNAL_DIR)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--per-page", type=int, default=12)
    args = parser.parse_args()
    return run(args.config, args.data_dir, args.signal_dir, args.timeout, args.per_page)


if __name__ == "__main__":
    raise SystemExit(main())
