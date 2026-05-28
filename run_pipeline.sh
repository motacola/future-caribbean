#!/usr/bin/env bash
# Full Caribbean Signal OS pipeline.
# Runs watchers, merger, channel packagers, and the operator console.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Caribbean Signal OS Pipeline ==="
echo ""

# Track step success for summary
FAILED=""

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
        echo "  ✗ ${label} (exit $rc)" >&2
        FAILED="$FAILED $label"
    fi
    echo ""
}

# ── Slow data (daily/weekly sources) ─────────────────────
run_step "World Bank" "python3 \"$ROOT/watchers/world_bank_poller.py\"" "world_bank"
run_step "IDB CKAN" "python3 \"$ROOT/watchers/idb_ckan_poller.py\"" "idb_ckan"
run_step "Tier 2 (CARICOM + CDB)" "python3 \"$ROOT/watchers/tier2_scraper.py\"" "tier2"

# ── Fast data (always runs) ───────────────────────────────
run_step "NOAA NWS" "python3 \"$ROOT/watchers/noaa_nws_poller.py\"" "noaa_nws"
run_step "NDBC Buoys" "python3 \"$ROOT/watchers/ndbc_buoy_poller.py\"" "ndbc_buoys"

# ── NHC Storm Intelligence ──────────────────────────────
run_step "NHC Storms" "python3 \"$ROOT/watchers/nhc_storm_poller.py\"" "nhc_storms"

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
run_step "Dispatch Desk" "python3 \"$ROOT/packagers/dispatch_desk.py\"" "dispatch_desk"
run_step "Telegram Brief" "python3 \"$ROOT/packagers/telegram_brief.py\"" "telegram_brief"

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

# ── Operator console ─────────────────────────────────────
run_step "Dashboard" "python3 \"$ROOT/dashboard/generate.py\" --no-open" "dashboard"

# ── Live delivery ────────────────────────────────────────
if [ -f "$ROOT/outbox/telegram_digest.md" ]; then
    run_step "Telegram Send" "python3 \"$ROOT/distributors/telegram_sender.py\" 2>&1 || echo \"Telegram: skipped (check credentials)\"" "telegram_send"
else
    echo "  ⚠ No telegram digest, skipping Telegram send"
fi


echo ""
echo "=== Pipeline complete ==="
echo "Packaged outputs: $ROOT/outbox/"
echo "Operator console: $ROOT/dashboard.html"
echo "Dispatch log:     $ROOT/outbox/live_send_log.md"
echo ""

if [ -n "$FAILED" ]; then
    echo "⚠ WARNING: These steps reported errors:$FAILED" >&2
    exit 1
fi

# Cleanup pipeline markers
rm -rf "$ROOT/.pipeline" 2>/dev/null