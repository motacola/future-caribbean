"""Deterministic official-source collector for Caribbean Market Watch.

This collector verifies public exchange pages and extracts only dated observations that
are explicitly present in the official page. It never manufactures prices or treats the
configured illustrative chart values as market history.
"""
from __future__ import annotations

import json
import re
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "market_sources.json"
OUT = ROOT / "data" / "market_watch" / "latest.json"
PUBLIC_SNAPSHOT = ROOT / "public" / "market_watch.json"
API_SNAPSHOT = ROOT / "api" / "market-watch-data.json"
TIMEOUT = 25
UA = {"User-Agent": "Mozilla/5.0 (compatible; SignalFabric/1.0; +https://signal-fabric.vercel.app)"}

SOURCE_PATHS = {
    "cayman": "https://www.csx.ky/trading/daily-trading-summary.asp",
}

SOURCE_DISCLOSURES = {
    "bahamas": "Official BISX homepage data is delayed by 30 minutes.",
}

DATE_PATTERNS = {
    "jamaica": (
        r"Market\s+(?:Open|Closed)\s+(\d{4}-\d{2}-\d{2})",
    ),
    "trinidad_tobago": (
        r"Activity\s+for\s+(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
        r"(\d{4}-\d{2}-\d{2})\s+00:00:00",
    ),
    "barbados": (
        r"Market\s+(?:open|closed)\s+(\d{4}-\d{2}-\d{2})",
    ),
    "bahamas": (
        r"Market\s+(?:Open|Closed).*?(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
    ),
    "cayman": (
        r"(?:Trade|Trading)\s+Date\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        r"\b(\d{4}-\d{2}-\d{2})\b",
    ),
    "eastern_caribbean": (
        r"Daily\s+Trade\s+Report[^\n]{0,80}?[–—-]\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
        r"\b(\d{4}-\d{2}-\d{2})\b",
    ),
}

STATUS_PATTERNS = {
    "jamaica": r"Market\s+(?:Open|Closed)\s+\d{4}-\d{2}-\d{2}[^\n]{0,110}",
    "trinidad_tobago": r"Activity\s+for\s+\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}[^\n]{0,110}",
    "barbados": r"Market\s+(?:open|closed)\s+\d{4}-\d{2}-\d{2}[^\n]{0,110}",
    "bahamas": r"Market\s+(?:Open|Closed)[^\n]{0,150}",
    "cayman": r"Daily\s+Trading\s+Summary[^\n]{0,110}",
    "eastern_caribbean": r"ECSE\s+Daily\s+Trade\s+Report[^\n]{0,120}",
}


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(?:script|style)\b[^>]*>.*?</(?:script|style)>", " ", raw)
    text = unescape(re.sub(r"<[^>]+>", " ", raw))
    return re.sub(r"[\t\r\f\v ]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()


def parse_date(value: str) -> datetime | None:
    cleaned = re.sub(r"\s+", " ", value.strip())
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def extract_observation(market_id: str, text: str) -> tuple[datetime | None, str | None]:
    observation = None
    for pattern in DATE_PATTERNS.get(market_id, ()):
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            observation = parse_date(match.group(1))
            if observation:
                break
    status_match = re.search(STATUS_PATTERNS.get(market_id, r"$^"), text, flags=re.IGNORECASE)
    status = re.sub(r"\s+", " ", status_match.group(0)).strip(" -–—|") if status_match else None
    if status and len(status) > 180:
        status = status[:177].rsplit(" ", 1)[0] + "…"
    return observation, status


def observation_state(observation: datetime | None, now: datetime | None = None) -> tuple[str, int | None]:
    if observation is None:
        return "source_checked_no_dated_observation", None
    now = now or datetime.now(timezone.utc)
    age_days = max(0, (now.date() - observation.date()).days)
    state = "current" if age_days <= 3 else "delayed" if age_days <= 10 else "stale"
    return state, age_days


def fetch_page(url: str) -> tuple[str, dict[str, str]]:
    context = ssl.create_default_context()
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=TIMEOUT, context=context) as response:
        raw = response.read(750_000).decode("utf-8", errors="replace")
        return raw, {key.lower(): value for key, value in response.headers.items()}


def collect_market(market: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    market_id = str(market.get("id") or "")
    exchange = market.get("exchange") or {}
    url = SOURCE_PATHS.get(market_id) or exchange.get("url")
    base = {
        "id": market_id,
        "country": market.get("country"),
        "exchange_code": exchange.get("code"),
        "exchange_name": exchange.get("name"),
        "source_url": url,
        "source_format": "public_html" if url else None,
        "machine_readable_feed": False,
        "timing_disclosure": SOURCE_DISCLOSURES.get(market_id),
        "attempted_at": now.isoformat(),
    }
    if not url:
        return {
            **base,
            "fetch_status": "not_applicable",
            "freshness_state": "proxy_watch",
            "observation_at": None,
            "observation_age_days": None,
            "summary": "No domestic exchange. Regional and cross-listed sources remain the explicit proxy watch.",
        }
    try:
        raw, headers = fetch_page(url)
        text = html_to_text(raw)
        observation, summary = extract_observation(market_id, text)
        state, age_days = observation_state(observation, now)
        return {
            **base,
            "fetch_status": "ok",
            "freshness_state": state,
            "observation_at": observation.date().isoformat() if observation else None,
            "observation_age_days": age_days,
            "summary": summary or "Official source reached; no dated market observation was exposed in the public page.",
            "response_date": headers.get("date"),
            "last_modified": headers.get("last-modified"),
        }
    except Exception as exc:
        return {
            **base,
            "fetch_status": "failed",
            "freshness_state": "unavailable",
            "observation_at": None,
            "observation_age_days": None,
            "summary": "Official source could not be refreshed in this collection attempt.",
            "error": f"{type(exc).__name__}: {exc}",
        }


def preserve_failed_market(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if current.get("fetch_status") != "failed" or not previous or not previous.get("observation_at"):
        return current
    return {
        **previous,
        "fetch_status": "fallback_cached",
        "freshness_state": "stale_fallback",
        "attempted_at": current.get("attempted_at"),
        "summary": "Refresh failed; serving the previous dated official observation as a preserved fallback.",
        "error": current.get("error"),
    }


def build_snapshot(now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    config = load_json(CONFIG, {})
    markets = list(config.get("markets") or [])
    previous = load_json(OUT, {})
    previous_by_id = {row.get("id"): row for row in previous.get("markets", [])}
    collected: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(collect_market, market, now): market for market in markets}
        for future in as_completed(futures):
            result = future.result()
            collected[result["id"]] = preserve_failed_market(result, previous_by_id.get(result["id"]))
    rows = [collected[str(market.get("id"))] for market in markets]
    network_rows = [row for row in rows if row.get("source_url")]
    healthy_states = {"current", "delayed", "stale", "source_checked_no_dated_observation"}
    return {
        "fetched_at": now.isoformat(),
        "source": "Official Caribbean exchange public pages",
        "method": "deterministic official-page verification; no inferred or synthetic prices",
        "health": {
            "configured_sources": len(network_rows),
            "successful_sources": sum(row.get("fetch_status") == "ok" for row in network_rows),
            "dated_observations": sum(bool(row.get("observation_at")) for row in network_rows),
            "current_observations": sum(row.get("freshness_state") == "current" for row in network_rows),
            "fallback_sources": sum(row.get("fetch_status") == "fallback_cached" for row in network_rows),
            "failed_sources": [row["id"] for row in network_rows if row.get("freshness_state") not in healthy_states and row.get("fetch_status") != "fallback_cached"],
        },
        "markets": rows,
    }


def write_snapshot(snapshot: dict[str, Any]) -> None:
    encoded = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
    for path in (OUT, PUBLIC_SNAPSHOT, API_SNAPSHOT):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded, encoding="utf-8")


def main() -> int:
    snapshot = build_snapshot()
    write_snapshot(snapshot)
    health = snapshot["health"]
    print(
        "market watch: "
        f"{health['successful_sources']}/{health['configured_sources']} official pages reached; "
        f"{health['current_observations']} current, {health['dated_observations']} dated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
