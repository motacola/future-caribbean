#!/usr/bin/env bash
# Full Caribbean Signal OS pipeline.
# Runs watchers, merger, channel packagers, and the operator console.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Caribbean Signal OS Pipeline ==="
echo ""

# Track step success for summary.
#
# Two classes of failure. External data sources are EXPECTED to be unavailable
# sometimes — feeds go down, keys expire, portals change shape — and the
# pipeline is built to degrade: watchers cache, the merger tolerates missing
# inputs, and the site renders "stale — fallback cached" states. Failing the
# whole run on one of those meant a single optional source with a missing API
# key silently blocked publication of everything else, which is how the site
# stopped updating.
#
# Only a failure in the steps that BUILD what the site serves should stop the
# publish.
FAILED=""
FAILED_OPTIONAL=""

# Steps that may fail without invalidating the cycle.
OPTIONAL_STEPS="World Bank|IDB CKAN|Tier 2 (CARICOM + CDB)|Tenders (Guyana eProcure + GOJEP)|Regional News RSS|CCRIF (Parametric Payouts)|ECCB (Monetary Stats)|Market Watch (exchanges)|NOAA NWS|NDBC Buoys|AIS Maritime|NHC Storms|Telegram Send|Webhook Alerts"

is_optional() {
    case "|$OPTIONAL_STEPS|" in
        *"|$1|"*) return 0 ;;
        *) return 1 ;;
    esac
}

run_step() {
    local label="$1"
    local cmd="$2"
    local marker="$3"
    echo "--- ${label} ---"
    if eval "$cmd" 2>&1; then
        echo "  ✓ ${label}"
        # Touch a marker file so later steps can validate
        if [ -n "$marker" ]; then
            mkdir -p "$ROOT/.pipeline"
            date -u +"%Y-%m-%dT%H:%M:%SZ" > "$ROOT/.pipeline/${marker}"
        fi
    else
        local rc=$?
        if is_optional "$label"; then
            echo "  ⚠ ${label} unavailable (exit $rc) — continuing on cached data" >&2
            FAILED_OPTIONAL="$FAILED_OPTIONAL $label"
        else
            echo "  ✗ ${label} (exit $rc)" >&2
            FAILED="$FAILED $label"
        fi
    fi
    echo ""
}

# ── Slow data (daily/weekly sources) ─────────────────────
run_step "World Bank" "python3 \"$ROOT/watchers/world_bank_poller.py\"" "world_bank"
run_step "IDB CKAN" "python3 \"$ROOT/watchers/idb_ckan_poller.py\"" "idb_ckan"
run_step "Tier 2 (CARICOM + CDB)" "python3 \"$ROOT/watchers/tier2_scraper.py\"" "tier2"
run_step "Tenders (Guyana eProcure + GOJEP)" "python3 \"$ROOT/watchers/tenders_poller.py\"" "tenders"
run_step "Regional News RSS" "python3 \"$ROOT/watchers/regional_news_poller.py\"" "regional_news"
run_step "News Image Enrichment" "python3 \"$ROOT/scripts/enrich_news_images.py\" --limit 30 --workers 3" "news_image_enrichment"
run_step "CCRIF (Parametric Payouts)" "python3 \"$ROOT/watchers/ccrif_poller.py\"" "ccrif"
run_step "ECCB (Monetary Stats)" "python3 \"$ROOT/watchers/eccb_poller.py\"" "eccb"
# Market Watch reads official exchange pages. It was never wired into the cycle,
# so data/market_watch/latest.json stayed frozen at whatever a hand run last
# produced — 22 days stale by 2026-09-04, while the desk still printed "current"
# against those observations. Running it per cycle refreshes the dated closes and,
# just as importantly, lets the poller downgrade an observation to stale_fallback
# once it ages, instead of the site asserting freshness it no longer has.
run_step "Market Watch (exchanges)" "python3 \"$ROOT/watchers/market_watch_poller.py\"" "market_watch"

# ── Fast data (always runs) ───────────────────────────────
run_step "NOAA NWS" "python3 \"$ROOT/watchers/noaa_nws_poller.py\"" "noaa_nws"
run_step "NDBC Buoys" "python3 \"$ROOT/watchers/ndbc_buoy_poller.py\"" "ndbc_buoys"
run_step "AIS Maritime" "python3 \"$ROOT/watchers/ais_poller.py\"" "ais_maritime"

# ── NHC Storm Intelligence ──────────────────────────────
run_step "NHC Storms" "python3 \"$ROOT/watchers/nhc_storm_poller.py\"" "nhc_storms"

# ── Source health bundle ─────────────────────────────────
# Must run after the watchers and before publication: data/*/latest.json is
# gitignored and .vercelignore'd, so this bundle is the only source-freshness
# signal that reaches production. Without it /api/status serves whatever
# timestamps were last committed by hand.
run_step "Source Health" "python3 \"$ROOT/packagers/source_health.py\"" "source_health"

# ── Cross-source merger ──────────────────────────────────
# Validate: at least one signal source should have completed
if [ ! -f "$ROOT/.pipeline/noaa_nws" ] && [ ! -f "$ROOT/.pipeline/ndbc_buoys" ] && [ ! -f "$ROOT/.pipeline/tier2" ]; then
    echo "  ⚠ No data sources completed. Merger may produce empty output."
fi
run_step "Composite Merger" "python3 \"$ROOT/mergers/cross_source_merger.py\"" "merger"

# ── Feedback loop (apply boosts from previous cycles) ────
run_step "Feedback Apply" "python3 \"$ROOT/packagers/feedback_loop.py\" apply" "feedback_apply"

# ── Packaging agents ─────────────────────────────────────
run_step "Channel Outputs" "python3 \"$ROOT/packagers/build_channel_outputs.py\"" "channel_outputs"
# ── Distribution delta ─────────────────────────────────────
# Intentionally not run here. Cron wrappers call distributors/delta_outbox.py
# once after this pipeline completes, so the hash gate is not consumed before
# Hermes can deliver the human-facing notification.

run_step "Opportunity Dispatch" "python3 \"$ROOT/packagers/opportunity_dispatch.py\"" "opportunity_dispatch"
# ── Procurement outcomes ─────────────────────────────────
# Folds this cycle's tender snapshot into the canonical corpus, then
# publishes the outcome view. The corpus is cumulative state like the
# calibration ledger: without it, latest.json's live snapshot is all we
# would ever know and no detection lead time could be proved.
run_step "Procurement Resolver" "python3 \"$ROOT/resolvers/procurement.py\"" "procurement_resolver"
run_step "Procurement Outcomes" "python3 \"$ROOT/packagers/procurement_outcomes.py\"" "procurement_outcomes"
run_step "Procurement Capability Matches" "python3 \"$ROOT/resolvers/capability_match.py\"" "capability_matches"

run_step "Coordination Graph" "python3 \"$ROOT/coordination/engine.py\"" "coordination_graph"
run_step "Validation Packs" "python3 \"$ROOT/packagers/validation_pack_generator.py\"" "validation_packs"
run_step "RSS Feed" "python3 \"$ROOT/packagers/rss_feed.py\"" "rss_feed"
run_step "Track Record" "python3 \"$ROOT/packagers/track_record.py\"" "track_record"
run_step "Calibration Ledger" "python3 \"$ROOT/packagers/calibration.py\"" "calibration"
run_step "Backtest Report" "python3 \"$ROOT/packagers/backtest_report.py\"" "backtest_report"
run_step "Dispatch Desk" "python3 \"$ROOT/packagers/dispatch_desk.py\"" "dispatch_desk"
run_step "Climate Dispatch (2nd instance)" "python3 \"$ROOT/packagers/climate_dispatch.py\"" "climate_dispatch"
run_step "Reasoning Agent (cross-signal synthesis)" "python3 \"$ROOT/reasoners/synthesis.py\"" "reasoning"
run_step "Telegram Brief" "python3 \"$ROOT/packagers/telegram_brief.py\"" "telegram_brief"
run_step "Community Brief" "python3 \"$ROOT/packagers/community_brief.py\"" "community_brief"

# ── Action Proof: Dispatch Packets & Delivery Manifest ───
run_step "Dispatch Packets" "python3 \"$ROOT/packagers/dispatch_packet_generator.py\"" "dispatch_packets"

# Validate dispatch packets exist before manifest
if [ -n "$(ls -A "$ROOT/outbox/dispatch_packets/"*.md 2>/dev/null)" ]; then
    run_step "Delivery Manifest" "python3 \"$ROOT/packagers/delivery_manifest.py\"" "delivery_manifest"
else
    echo "  ⚠ No dispatch packets found, skipping delivery manifest"
fi

# ── Editorial calendar (why now?) ────────────────────────
run_step "Why Now Context" "python3 \"$ROOT/packagers/editorial_calendar.py\"" "editorial_calendar"

# ── Cross-cluster synthesis ──────────────────────────────
run_step "Regional Thesis" "python3 \"$ROOT/packagers/regional_thesis.py\"" "regional_thesis"

# ── Feedback loop (record cycle history) ─────────────────
if [ -f "$ROOT/outbox/opportunity_dispatches.json" ]; then
    run_step "Feedback Record" "python3 \"$ROOT/packagers/feedback_loop.py\" record --file \"$ROOT/outbox/opportunity_dispatches.json\"" "feedback_record"
else
    echo "  ⚠ No dispatches file, skipping feedback record"
fi

# ── Legacy feedback collector ────────────────────────────
run_step "Feedback Collector" "python3 \"$ROOT/distributors/feedback_collector.py\"" "feedback_collector"

# ── Operator console (Astro build; data baked in from outbox/ via src/lib/data.ts) ──
if command -v pnpm >/dev/null 2>&1; then
    run_step "Dashboard" "pnpm --dir \"$ROOT\" build" "dashboard"
else
    echo "  ⚠ pnpm not found, skipping Astro dashboard build (dist/ may be stale)"
fi

# ── Live delivery ────────────────────────────────────────
if [ -f "$ROOT/outbox/telegram_digest.md" ]; then
    run_step "Telegram Send" "python3 \"$ROOT/distributors/telegram_sender.py\" 2>&1 || echo \"Telegram: skipped (check credentials)\"" "telegram_send"
else
    echo "  ⚠ No telegram digest, skipping Telegram send"
fi

# ── Webhook alerts ────────────────────────────────────────
run_step "Webhook Alerts" "python3 \"$ROOT/packagers/webhook_notifier.py\"" ""


echo ""
echo "=== Pipeline complete ==="
echo "Packaged outputs: $ROOT/outbox/"
echo "Operator console: $ROOT/dist/index.html (serve with: python3 server.py)"
echo "Dispatch log:     $ROOT/outbox/live_send_log.md"
echo ""

if [ -n "$FAILED_OPTIONAL" ]; then
    echo "⚠ Optional sources unavailable this cycle:$FAILED_OPTIONAL" >&2
    echo "  The cycle still published; affected surfaces show cached/stale state." >&2
fi

if [ -n "$FAILED" ]; then
    echo "✗ ESSENTIAL steps failed:$FAILED" >&2
    echo "  Refusing to publish — the artefacts would not reflect a complete cycle." >&2
    exit 1
fi

# Cleanup pipeline markers
rm -rf "$ROOT/.pipeline" 2>/dev/null