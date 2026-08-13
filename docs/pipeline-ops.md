# Pipeline operations runbook

## Status (as of 2026-08-13)

**GitHub Actions scheduled cron has been failing for ~2.5 months** (last
successful run: 2026-05-31T16:57:23Z). The failure mode is the same for
every scheduled run since then:

> "The job was not started because recent account payments have failed
> or your spending limit needs to be increased."

This is a **GitHub account billing issue**, not a code issue. The
workflow file (`.github/workflows/pipeline.yml`) is structurally complete
and was last verified working in May 2026.

## What to do

1. Visit https://github.com/settings/billing/plans (or the org's billing
   page) and check whether the Actions spending limit needs to be raised
   or there's an unpaid invoice.
2. Once billing is restored, the next `cron` tick (`7 */4 * * *` — every
   4 hours at :07 past the hour) will fire automatically. No code change
   needed.
3. To fire immediately, click "Run workflow" on
   https://github.com/motacola/future-caribbean/actions/workflows/pipeline.yml
   or:
   ```bash
   gh workflow run pipeline.yml
   ```

## Local fallback (works today)

If you can't restore billing immediately, the pipeline can be run locally
on a cron of your choice:

```bash
cd /Users/christopherbelgrave/clawd/projects/future-caribbean

# Run individual stages — NEVER run the full run_pipeline.sh from a local
# session because it sends Telegram notifications (skill rule).
python3 watchers/noaa_nws_poller.py
python3 watchers/ndbc_buoy_poller.py
python3 watchers/world_bank_poller.py
python3 watchers/idb_ckan_poller.py
python3 watchers/tier2_scraper.py
python3 watchers/ccrif_poller.py
python3 watchers/eccb_poller.py
python3 watchers/tenders_poller.py
python3 watchers/market_watch_poller.py
python3 watchers/regional_news_poller.py
python3 mergers/cross_source_merger.py
python3 packagers/feedback_loop.py apply
python3 packagers/build_channel_outputs.py
python3 packagers/opportunity_dispatch.py
python3 coordination/engine.py
python3 packagers/validation_pack_generator.py
python3 packagers/track_record.py
python3 packagers/dispatch_desk.py
python3 packagers/climate_dispatch.py
python3 reasoners/synthesis.py
python3 packagers/regional_thesis.py
python3 packagers/dispatch_packet_generator.py
python3 packagers/delivery_manifest.py
python3 packagers/feedback_loop.py record --file outbox/opportunity_dispatches.json
python3 packagers/editorial_calendar.py
python3 packagers/rss_feed.py
python3 scripts/build_source_health_snapshot.py
```

Then commit the updated `data/`, `outbox/`, `api/*-data.json`,
`public/market_watch.json` artifacts and push to main. Vercel will
auto-deploy.

## Skipped local watchers (need configuration)

These are intentionally NOT in the local-fallback list because they
require credentials Chris hasn't provided yet:

- **`watchers/ais_poller.py`** — needs `AISSTREAM_API_KEY` env var.
  Free at https://aisstream.io (after signup). Without it, the poller
  prints `AISSTREAM_API_KEY not set` and writes a 0-row snapshot. The
  AIS layer (vessel positions, port density, shipping corridors) won't
  appear on the dashboard until this key is set in both the local env
  AND in the GitHub Actions secrets (and Vercel env if you want the
  AIS feed in `data/ais/latest.json` to be visible live — currently
  `data/ais/*` is `.vercelignore`'d).

- **`watchers/tenders_poller.py`** — works without auth but the
  Jamaica GOJEP `contract awards` endpoint requires a session cookie;
  the poller gracefully falls back to its cache when that endpoint is
  unreachable. No action needed unless you want fresh Jamaica contract
  awards every cycle.

- **`watchers/regional_news_poller.py` Google News feeds** — Google
  occasionally rate-limits or blocks cloud IPs. The poller keeps its
  prior-good cache when this happens. If you see
  `google-news-* unreachable` for several consecutive runs, the local
  Python SSL bundle needs `certifi` (`pip install certifi`) — handled
  by the `_ssl_context()` helper added 2026-08-13.

## Verification

After any pipeline run (local or GitHub Actions), confirm freshness on
the live site:

```bash
curl -s https://signal-fabric.vercel.app/api/status | python3 -m json.tool
```

Expected:

- `cycle_id` matches today's date (YYYYMMDD format)
- `n_sources_ok == n_sources_total` (all 6 healthy)
- `sources[].age_minutes` is small for the watchers you just ran

If `n_sources_ok < n_sources_total`, the poller for one source failed
silently — check `signals/<source>/latest.md` for the error.