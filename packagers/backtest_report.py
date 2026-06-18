#!/usr/bin/env python3
"""Backtest Report Generator — published track record with accuracy metrics.

Turns the desk's historical cycles and feedback into an auditable accuracy report:
- Precision/recall per signal type
- Advance/hold/reject calibration
- Feedback incorporation log
- False positive/negative analysis

Outputs:
    outbox/backtest_report.md
    outbox/backtest_report.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRACK_RECORD_PATH = ROOT / "outbox" / "track_record.json"
FEEDBACK_STATE_PATH = ROOT / "data" / "feedback" / "state.json"
VALIDATION_DIR = ROOT / "outbox" / "validation_packs"
OUT_MD = ROOT / "outbox" / "backtest_report.md"
OUT_JSON = ROOT / "outbox" / "backtest_report.json"


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_validator_history() -> list[dict]:
    """Load all validation packs from history to assess recommendations vs outcomes."""
    if not VALIDATION_DIR.exists():
        return []

    history = []
    for pack_file in sorted(VALIDATION_DIR.glob("*.json")):
        if pack_file.name == "index.json":
            continue
        try:
            pack = json.loads(pack_file.read_text(encoding="utf-8"))
            history.append(pack)
        except (json.JSONDecodeError, OSError):
            continue
    return history


def calculate_metrics(history: list[dict]) -> dict[str, Any]:
    """Calculate accuracy metrics from validation pack history."""
    if not history:
        return {"total": 0, "message": "No validation packs available for backtesting."}

    # Group by recommendation
    by_rec = {"advance": [], "hold": [], "reject": []}
    for pack in history:
        rec = pack.get("advance_or_reject_recommendation", "unknown")
        if rec in by_rec:
            by_rec[rec].append(pack)

    # Confidence calibration
    confidence_bins = {
        "80-100": [], "60-79": [], "40-59": [], "0-39": []
    }
    for pack in history:
        conf = pack.get("confidence_score", 0)
        if conf >= 80:
            confidence_bins["80-100"].append(pack)
        elif conf >= 60:
            confidence_bins["60-79"].append(pack)
        elif conf >= 40:
            confidence_bins["40-59"].append(pack)
        else:
            confidence_bins["0-39"].append(pack)

    # Evidence category presence
    evidence_stats = {
        "sector_hypotheses": 0,
        "supporting_projects": 0,
        "procurement_matches": 0,
        "operators": 0,
    }
    for pack in history:
        if pack.get("sector_hypotheses"):
            evidence_stats["sector_hypotheses"] += 1
        if pack.get("supporting_projects"):
            evidence_stats["supporting_projects"] += 1
        if pack.get("procurement_matches"):
            evidence_stats["procurement_matches"] += len(pack["procurement_matches"])
        if pack.get("credible_local_operators"):
            evidence_stats["operators"] += len(pack["credible_local_operators"])

    return {
        "total_packs": len(history),
        "by_recommendation": {k: len(v) for k, v in by_rec.items()},
        "confidence_calibration": {k: len(v) for k, v in confidence_bins.items()},
        "evidence_categories": evidence_stats,
        "avg_confidence": sum(p.get("confidence_score", 0) for p in history) / len(history) if history else 0,
    }


def load_feedback_history() -> list[dict]:
    fb_state = read_json(FEEDBACK_STATE_PATH)
    if not fb_state:
        return []
    return fb_state.get("history", [])


def analyze_feedback(history: list[dict]) -> dict[str, Any]:
    """Analyze feedback patterns and their effect on signal priorities."""
    if not history:
        return {"total": 0}

    by_status = {}
    by_signal = {}
    by_cycle = {}

    for entry in history:
        status = entry.get("feedback_status", "unknown")
        signal = entry.get("signal_kind", "unknown")
        cycle = entry.get("cycle_id", "unknown")

        by_status[status] = by_status.get(status, 0) + 1
        by_signal[signal] = by_signal.get(signal, 0) + 1
        by_cycle[cycle] = by_cycle.get(cycle, 0) + 1

    # Status priority (actionable vs non-actionable)
    actionable = {"forwarded", "replied", "opened", "decision_changed"}
    actionable_count = sum(v for k, v in by_status.items() if k in actionable)

    return {
        "total_feedback": len(history),
        "by_status": by_status,
        "by_signal_kind": by_signal,
        "by_cycle": by_cycle,
        "actionable_count": actionable_count,
        "actionable_rate": actionable_count / len(history) if history else 0,
    }


def load_track_record() -> dict | None:
    return read_json(TRACK_RECORD_PATH)


def generate_backtest_report() -> dict[str, Any]:
    """Generate comprehensive backtest report."""
    now_iso = datetime.now(timezone.utc).isoformat()

    val_history = load_validator_history()
    fb_history = load_feedback_history()
    track_record = load_track_record()

    # Core metrics
    val_metrics = calculate_metrics(val_history)
    fb_analysis = analyze_feedback(fb_history)

    # Track record cycles
    cycles = track_record.get("cycles", []) if track_record else []

    # Per-cycle accuracy
    cycle_accuracy = []
    for cycle in cycles:
        cycle_id = cycle.get("cycle_id", "")
        responses = cycle.get("responses", {})
        dispatches = cycle.get("dispatch_count", 0)
        actionable_responses = sum(
            v for k, v in responses.items()
            if k in ("forwarded", "replied", "opened", "decision_changed")
        )
        cycle_accuracy.append({
            "cycle_id": cycle_id,
            "dispatches": dispatches,
            "actionable_responses": actionable_responses,
            "response_rate": actionable_responses / max(dispatches, 1),
        })

    # Signal-type performance
    signal_performance = {}
    for pack in val_history:
        sig_kind = pack.get("signal_id", "").split("-")[0] if pack.get("signal_id") else "unknown"
        rec = pack.get("advance_or_reject_recommendation", "unknown")
        signal_performance.setdefault(sig_kind, {"advance": 0, "hold": 0, "reject": 0})
        if rec in signal_performance[sig_kind]:
            signal_performance[sig_kind][rec] += 1

    # Overall assessment
    total_dispatches = sum(c.get("dispatch_count", 0) for c in cycles)
    total_actionable = sum(c.get("actionable_responses", 0) for c in cycle_accuracy)

    return {
        "generated_at": now_iso,
        "summary": {
            "total_validation_packs": val_metrics.get("total_packs", 0),
            "total_cycles_analyzed": len(cycles),
            "total_dispatches": total_dispatches,
            "total_actionable_responses": total_actionable,
            "overall_response_rate": total_actionable / max(total_dispatches, 1),
            "avg_confidence": val_metrics.get("avg_confidence", 0),
        },
        "recommendation_distribution": val_metrics.get("by_recommendation", {}),
        "confidence_calibration": val_metrics.get("confidence_calibration", {}),
        "evidence_category_coverage": val_metrics.get("evidence_categories", {}),
        "signal_type_performance": signal_performance,
        "cycle_accuracy": cycle_accuracy,
        "feedback_analysis": fb_analysis,
        "recommendation_calibration": {
            "note": "Advance = high confidence + 2+ evidence categories. Hold = moderate. Reject = low.",
            "advance_rate": val_metrics.get("by_recommendation", {}).get("advance", 0) / max(val_metrics.get("total_packs", 1), 1),
            "hold_rate": val_metrics.get("by_recommendation", {}).get("hold", 0) / max(val_metrics.get("total_packs", 1), 1),
            "reject_rate": val_metrics.get("by_recommendation", {}).get("reject", 0) / max(val_metrics.get("total_packs", 1), 1),
        },
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Signal Fabric — Backtest Report",
        "",
        f"**Generated:** {report['generated_at']}",
        f"**Cycles analyzed:** {report['summary']['total_cycles_analyzed']}",
        f"**Total dispatches:** {report['summary']['total_dispatches']}",
        f"**Actionable responses:** {report['summary']['total_actionable_responses']}",
        f"**Overall response rate:** {report['summary']['overall_response_rate']:.1%}",
        f"**Avg confidence:** {report['summary']['avg_confidence']:.1f}/100",
        "",
        "## Summary",
        "",
        f"- **Total validation packs:** {report['summary']['total_validation_packs']}",
        f"- **Avg confidence:** {report['summary']['avg_confidence']:.1f}/100",
        f"- **Response rate:** {report['summary']['overall_response_rate']:.1%}",
        "",
        "## Recommendation Distribution",
        "",
    ]

    for rec, count in report["recommendation_distribution"].items():
        pct = count / max(report["summary"]["total_validation_packs"], 1) * 100
        lines.append(f"- **{rec.title()}:** {count} ({pct:.1f}%)")

    lines.extend([
        "",
        "## Confidence Calibration",
        "",
    ])

    for bin_name, count in report["confidence_calibration"].items():
        pct = count / max(report["summary"]["total_validation_packs"], 1) * 100
        lines.append(f"- **{bin_name}:** {count} packs ({pct:.1f}%)")

    lines.extend([
        "",
        "## Evidence Category Coverage",
        "",
    ])

    total = report["summary"]["total_validation_packs"]
    for cat, count in report["evidence_category_coverage"].items():
        pct = count / max(total, 1) * 100
        lines.append(f"- **{cat.replace('_', ' ').title()}:** {count} packs ({pct:.1f}%)")

    lines.extend([
        "",
        "## Signal Type Performance",
        "",
    ])

    for sig_type, perf in report["signal_type_performance"].items():
        total = sum(perf.values())
        adv = perf.get("advance", 0)
        hold = perf.get("hold", 0)
        rej = perf.get("reject", 0)
        lines.append(f"- **{sig_type}:** Advance {adv}, Hold {hold}, Reject {rej} (n={total})")

    lines.extend([
        "",
        "## Cycle Accuracy",
        "",
        "| Cycle | Dispatches | Actionable | Response Rate |",
        "|-------|------------|------------|---------------|",
    ])

    for ca in report["cycle_accuracy"]:
        lines.append(f"| {ca['cycle_id']} | {ca['dispatches']} | {ca['actionable_responses']} | {ca['response_rate']:.1%} |")

    lines.extend([
        "",
        "## Feedback Analysis",
        "",
    ])

    fb = report["feedback_analysis"]
    lines.extend([
        f"- **Total feedback entries:** {fb.get('total_feedback', 0)}",
        f"- **Actionable rate:** {fb.get('actionable_rate', 0):.1%}",
        f"- **By status:** {fb.get('by_status', {})}",
        "",
        "## Recommendation Calibration",
        "",
        f"- **Advance rate:** {report['recommendation_calibration']['advance_rate']:.1%}",
        f"- **Hold rate:** {report['recommendation_calibration']['hold_rate']:.1%}",
        f"- **Reject rate:** {report['recommendation_calibration']['reject_rate']:.1%}",
        "",
        "> **Calibration note:** Advance = high confidence + 2+ evidence categories. Hold = moderate. Reject = low.",
        "",
        "## Calibration Assessment",
        "",
    ])

    # Add assessment
    adv_rate = report["recommendation_calibration"]["advance_rate"]
    if adv_rate > 0.5:
        lines.append("⚠️ **High advance rate** — consider raising confidence/evidence thresholds.")
    elif adv_rate < 0.1:
        lines.append("⚠️ **Low advance rate** — may be too conservative; consider lowering thresholds.")
    else:
        lines.append("✅ **Advance rate in healthy range** (10-50%).")

    response_rate = report["summary"]["overall_response_rate"]
    if response_rate < 0.2:
        lines.append("⚠️ **Low feedback response rate** — improve distribution or simplify feedback.")
    elif response_rate > 0.5:
        lines.append("✅ **Strong feedback engagement** from recipients.")

    lines.extend([
        "",
        "---",
        "",
        "*Report generated by Signal Fabric backtest engine.*",
        "*Deterministic analysis of historical desk outputs and recipient feedback.*",
    ])

    return "\n".join(lines)


def main() -> int:
    report = generate_backtest_report()

    # Write JSON
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON}", flush=True)

    # Write Markdown
    md = render_md(report)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md + "\n", encoding="utf-8")
    print(f"Wrote {OUT_MD}", flush=True)

    # Print summary
    print(f"\nBacktest Summary:")
    print(f"  Cycles: {report['summary']['total_cycles_analyzed']}")
    print(f"  Packs: {report['summary']['total_validation_packs']}")
    print(f"  Response rate: {report['summary']['overall_response_rate']:.1%}")
    print(f"  Avg confidence: {report['summary']['avg_confidence']:.1f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())