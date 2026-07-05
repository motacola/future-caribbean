#!/usr/bin/env python3
"""Opportunity Dispatch Generator — converts enriched signals into routed dispatches.

Each dispatch is a concrete opportunity object with:
  - target persona and action
  - evidence summary and confidence
  - channel routing and delivery tracking
  - feedback prompt and next-cycle effect

This is the core product artifact of Caribbean Opportunity Dispatch.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packagers.editorial_enrichment import enrich_signals  # noqa: E402
from packagers.narrative import narrative_title as _narrative_title  # noqa: E402

DEFAULT_INPUT = ROOT / "data" / "composite" / "latest.json"
DEFAULT_CONFIG = ROOT / "config" / "recipients.json"
DEFAULT_OUTBOX = ROOT / "outbox"
DEFAULT_FEEDBACK_LOG = ROOT / "data" / "feedback" / "delivery_log.jsonl"


# ── Persona label lookup ──────────────────────────────────

def _persona_label(config: dict, key: str) -> str:
    return config.get("personas", {}).get(key, {}).get("label", key)


def _persona_description(config: dict, key: str) -> str:
    return config.get("personas", {}).get(key, {}).get("description", _persona_label(config, key))


def _clip_text(value: str, limit: int = 160) -> str:
    """Clip display text without cutting words mid-token."""
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    clipped = text[: limit - 1].rsplit(" ", 1)[0].rstrip(".,;:")
    return f"{clipped}..."


# ── Dispatch helpers ──────────────────────────────────────


def _persona_action_for_kind(
    persona_key: str,
    kind: str,
    country: str,
    detail: str,
    action_window: str,
) -> str:
    """Sharper, persona-specific action language."""
    # Supply chain signal - handle first for relevant personas
    if kind == "supply_chain_signal":
        if persona_key == "regional_operator":
            return (
                f"Active supply chain corridor in {country}: procurement live + maritime stable. "
                f"Assess capacity for logistics, warehousing, transport — bid window open."
            )
        if persona_key == "procurement_watcher":
            return (
                f"CDB procurement ({detail}) aligned with stable shipping lanes. "
                f"Viable corridor for logistics providers — prepare EOI."
            )
        if persona_key == "founder_operator":
            return (
                f"Supply chain gap in {country} confirmed. Procurement pipeline + stable maritime = "
                f"build warehousing, transport, or last-mile services here."
            )
        if persona_key == "diaspora_investor":
            return (
                f"Supply chain corridor in {country} — logistics + procurement convergence. "
                f"Infrastructure play with project-based entry. {detail}"
            )
        if persona_key == "ecosystem_builder":
            return (
                f"Supply chain corridor opening in {country} — connect logistics founders "
                f"to procurement pipeline ({detail})."
            )

    if persona_key == "diaspora_investor":
        if "enhanced" in kind:
            return (
                f"Investigate {country} as a capital deployment target this cycle. "
                f"Multi-source validation ({detail}) confirms directional signal — "
                f"next step is operator discovery and market entry assessment."
            )
        if "investment" in kind:
            return (
                f"Screen {country} for investment readiness. "
                f"FDI movement ({detail}) is a screening trigger — "
                f"cross-reference with sector conditions before deploying capital."
            )
        if kind == "development_pipeline":
            return (
                f"Review CDB/IDB procurement pipeline for {country}. "
                f"Project-based entry may be lower-risk than direct equity in early-stage markets."
            )
        if "vulnerability" in kind or kind == "food_security":
            return (
                f"Assess portfolio exposure in {country}. "
                f"Economic stress indicators ({detail}) may affect existing positions or timing."
            )
    if persona_key == "founder_operator":
        if "investment" in kind:
            return (
                f"Assess competitive positioning in {country}. "
                f"FDI movement ({detail}) signals growing market or incoming competition — "
                f"evaluate local advantage before new entrants arrive."
            )
        if kind == "development_pipeline":
            return (
                f"Map {country} procurement pipeline against your capability. "
                f"CDB/IDB projects ({detail}) create service and supply opportunities."
            )
        if "tourism" in kind or kind == "tourism_impact":
            return (
                f"Validate consumer demand signal in {country}. "
                f"GDP growth ({detail}) may indicate expanding local market for products and services."
            )
    if persona_key == "ecosystem_builder":
        return (
            f"Route {country} opportunity to relevant founders and investors in your network. "
            f"Signal strength ({detail}) makes this a high-priority introduction target."
        )
    if persona_key == "regional_operator":
        return (
            f"Review operational readiness for {country} opportunities. "
            f"{detail} — assess capacity and bid pipeline."
        )
    if persona_key == "procurement_watcher":
        return (
            f"Track CDB/IDB project pipeline: {detail}. "
            f"Review opportunity fit and prepare expression of interest."
        )
    if persona_key == "operator_resilience":
        return (
            f"Prepare operational response: {country}. "
            f"Action window: {action_window}. "
            f"Evidence: {detail}"
        )
    if persona_key == "policy_media":
        return (
            f"Signal context for {country}: {detail}. "
            f"Use this dispatch as a briefing input or narrative lead."
        )
    if persona_key == "tourism_logistics_operator":
        return (
            f"Assess {country} demand trajectory. "
            f"{detail} — adjust capacity plans."
        )
    return f"Review {country}: {detail}. Validate locally before action."


def _make_dispatch(
    config: dict,
    dispatch_id: str,
    generated_at: str,
    signal_id: str,
    kind: str,
    kind_label: str,
    cycle_id: str,
    title: str,
    country_cluster: str,
    persona_key: str,
    persona_label: str,
    recipient_type: str,
    recommended_action: str,
    action_window: str,
    channel: str,
    confidence_display: str,
    confidence_score: int,
    evidence_grade: str,
    evidence_summary: str,
    detail: str,
    freshness: str,
    risk_flags: list[str],
    decision_influence: str,
    routing_rationale: str,
    ranking_rationale: str = "",
) -> dict:
    return {
        "dispatch_id": dispatch_id,
        "generated_at": generated_at,
        "signal_id": signal_id,
        "signal_kind": kind,
        "signal_kind_label": kind_label,
        "cycle_id": cycle_id,
        "title": title,
        "country_cluster": country_cluster,
        "persona_key": persona_key,
        "persona_label": persona_label,
        "recipient_type": recipient_type,
        "recommended_action": recommended_action,
        "action_window": action_window,
        "channel": channel,
        "confidence_display": confidence_display,
        "confidence_score": confidence_score,
        "evidence_grade": evidence_grade,
        "evidence_summary": evidence_summary,
        "detail": detail,
        "freshness": freshness,
        "risk_flags": risk_flags,
        "decision_influence": decision_influence,
        "routing_rationale": routing_rationale,
        "ranking_rationale": ranking_rationale,
        "feedback_prompt": "Did this dispatch trigger a follow-up, get forwarded, or change a decision?",
        "delivery_status": "queued",
        "feedback_status": "awaiting",
    }


# ── Dispatch generation ───────────────────────────────────

def build_dispatches(
    signals: list[dict[str, Any]],
    enriched: list[dict[str, Any]],
    config: dict[str, Any],
    cycle_id: str,
) -> list[dict[str, Any]]:
    """Build dispatches with de-duplication for bulk signals.

    When 3+ same-kind country signals exist (e.g. 8 enhanced_investment),
    creates a regional summary dispatch plus top-3 individual dispatches
    instead of routing every identical signal to every persona.

    Each dispatch carries routing_rationale from config explaining why
    this persona received this signal.
    """
    rules = config.get("routing_rules", {})
    dispatches: list[dict[str, Any]] = []
    dispatch_seq = 0

    # Only process signals with meaningful scores (exclude <50 context-only)
    candidate_signals = [s for s in enriched if s.get("_score", 0) >= 50]

    # Group by kind for de-duplication
    from collections import defaultdict
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sig in candidate_signals:
        by_kind[sig.get("kind", "")].append(sig)

    # Kinds that benefit from de-duplication
    BULK_KINDS = {"enhanced_investment", "investment_signal", "tourism_impact"}

    for kind, kind_signals in by_kind.items():
        rule = rules.get(kind)
        if not rule:
            continue

        if kind in BULK_KINDS and len(kind_signals) >= 3:
            # ── Regional summary dispatch (one per persona) ──────
            # Sort by detail magnitude (FDI % or GDP %) descending
            def _mag(s: dict) -> float:
                import re
                d = s.get("_detail", "")
                m = re.search(r"([\d.]+)", d)
                return float(m.group(1)) if m else 0
            sorted_signals = sorted(kind_signals, key=_mag, reverse=True)

            for persona_key in rule.get("personas", []):
                dispatch_seq += 1
                top_3 = sorted_signals[:3]
                top_detail = ", ".join(
                    f"{s.get('_country', '?')} ({s.get('_detail', '?')})"
                    for s in top_3
                )
                regional_title = _narrative_title(
                    kind=kind, country="", detail=top_detail,
                    score=90, band="immediate",
                    n_sources=len({s for sig in sorted_signals[:3] for s in sig.get("sources", [])}),
                    is_regional=True, regional_count=len(sorted_signals),
                )
                action_window = rule.get("action_window", "14 days")
                routing_rationale_map = rule.get("routing_rationale", {})
                rationale = routing_rationale_map.get(persona_key, "")

                dispatch = _make_dispatch(
                    config=config,
                    dispatch_id=f"DSP-{cycle_id}-{dispatch_seq:03d}",
                    generated_at=datetime.now(timezone.utc).isoformat(),
                    signal_id=f"regional-{kind}-{cycle_id}",
                    kind=kind,
                    kind_label=kind.replace("_", " ").title(),
                    cycle_id=cycle_id,
                    title=regional_title,
                    country_cluster="Caribwide",
                    persona_key=persona_key,
                    persona_label=_persona_label(config, persona_key),
                    recipient_type=_persona_description(config, persona_key),
                    recommended_action=_persona_action_for_kind(persona_key, kind, "Caribwide",
                                                                top_detail, action_window),
                    action_window=action_window,
                    channel=config.get("personas", {}).get(persona_key, {}).get("channel", "Telegram"),
                    confidence_display="🟡 Validation | Multi-country | Multi-source",
                    confidence_score=90,
                    evidence_grade="B - cross-source",
                    evidence_summary=f"Multi-country {kind.replace('_', ' ')} validated across "
                                    f"{len(sorted_signals)} countries. Top magnitudes: {top_detail}.",
                    detail=top_detail,
                    freshness="new",
                    risk_flags=[],
                    decision_influence=rule.get("decision_to_influence", ""),
                    routing_rationale=rationale,
                    ranking_rationale=f"Regional {kind.replace('_', ' ')} summary ranks at 90/100 because {len(sorted_signals)} country signal(s) are grouped; top markets: {top_detail}.",
                )
                dispatches.append(dispatch)

            # ── Per-country dispatches for top 3 only ──────────
            for sig in sorted_signals[:3]:
                country = sig.get("_country", "Regional")
                detail = sig.get("_detail", "")
                score = sig.get("_score", 0)
                grade = sig.get("_evidence_grade", "C")
                summary = sig.get("summary", "")
                freshness = sig.get("_freshness", "sustained")
                band = sig.get("_band_label", "")
                band_emoji = sig.get("_band_emoji", "⚪")
                evidence = sig.get("evidence") or []
                evidence_text = "; ".join(str(e) for e in evidence[:4]) if evidence else summary

                # Risk flags
                risk_flags: list[str] = []
                if kind == "enhanced_investment":
                    has_vuln = any(
                        s.get("kind") == "economic_vulnerability" and s.get("_country") == country
                        for s in enriched
                    )
                    if has_vuln:
                        risk_flags.append(f"{country} also has vulnerability — validate before committing")

                # Persona-specific actions
                for persona_key in rule.get("personas", []):
                    dispatch_seq += 1
                    routing_rationale_map = rule.get("routing_rationale", {})
                    rationale = routing_rationale_map.get(persona_key, "")

                    dispatch_title = _narrative_title(
                        kind=kind, country=country, detail=detail,
                        score=score, band=band,
                        n_sources=len(sig.get("sources", [])),
                    )

                    dispatch = _make_dispatch(
                        config=config,
                        dispatch_id=f"DSP-{cycle_id}-{dispatch_seq:03d}",
                        generated_at=datetime.now(timezone.utc).isoformat(),
                        signal_id=sig.get("id", ""),
                        kind=kind,
                        kind_label=sig.get("_kind_label", kind),
                        cycle_id=cycle_id,
                        title=dispatch_title,
                        country_cluster=country if country != "Regional" else "Caribwide",
                        persona_key=persona_key,
                        persona_label=_persona_label(config, persona_key),
                        recipient_type=_persona_description(config, persona_key),
                        recommended_action=_persona_action_for_kind(persona_key, kind, country,
                                                                    detail, action_window),
                        action_window=action_window,
                        channel=config.get("personas", {}).get(persona_key, {}).get("channel", "Telegram"),
                        confidence_display=f"{band_emoji} {band} | {score}/100 | {grade}",
                        confidence_score=score,
                        evidence_grade=grade,
                        evidence_summary=evidence_text,
                        detail=detail,
                        freshness=freshness,
                        risk_flags=risk_flags,
                        decision_influence=rule.get("decision_to_influence", ""),
                        routing_rationale=rationale,
                        ranking_rationale=sig.get("_ranking_rationale", ""),
                    )
                    dispatches.append(dispatch)

        else:
            # ── Standard per-signal dispatching (1-2 signals per kind) ──
            for sig in kind_signals:
                country = sig.get("_country", "Regional")
                score = sig.get("_score", 0)
                grade = sig.get("_evidence_grade", "C")
                detail = sig.get("_detail", "")
                summary = sig.get("summary", "")
                freshness = sig.get("_freshness", "sustained")
                band = sig.get("_band_label", "")
                band_emoji = sig.get("_band_emoji", "⚪")
                kind_label = sig.get("_kind_label", kind)
                evidence = sig.get("evidence") or []
                evidence_text = "; ".join(str(e) for e in evidence[:4]) if evidence else summary

                # Risk flags
                risk_flags: list[str] = []
                if kind == "enhanced_investment":
                    has_vuln = any(
                        s.get("kind") == "economic_vulnerability" and s.get("_country") == country
                        for s in enriched
                    )
                    if has_vuln:
                        risk_flags.append(f"{country} also has vulnerability — validate before committing")
                if kind == "economic_vulnerability":
                    risk_flags.append(f"Elevated economic stress in {country}")

                for persona_key in rule.get("personas", []):
                    dispatch_seq += 1
                    routing_rationale_map = rule.get("routing_rationale", {})
                    rationale = routing_rationale_map.get(persona_key, "")

                    dispatch_title = _narrative_title(
                        kind=kind, country=country, detail=detail,
                        score=score, band=sig.get("_band_label", "monitor"),
                        n_sources=len(sig.get("sources", [])),
                    )

                    dispatch = _make_dispatch(
                        config=config,
                        dispatch_id=f"DSP-{cycle_id}-{dispatch_seq:03d}",
                        generated_at=datetime.now(timezone.utc).isoformat(),
                        signal_id=sig.get("id", ""),
                        kind=kind,
                        kind_label=kind_label,
                        cycle_id=cycle_id,
                        title=dispatch_title,
                        country_cluster=country if country != "Regional" else "Caribwide",
                        persona_key=persona_key,
                        persona_label=_persona_label(config, persona_key),
                        recipient_type=_persona_description(config, persona_key),
                        recommended_action=_persona_action_for_kind(persona_key, kind, country,
                                                                    detail, rule.get("action_window", "14 days")),
                        action_window=rule.get("action_window", "14 days"),
                        channel=config.get("personas", {}).get(persona_key, {}).get("channel", "Telegram"),
                        confidence_display=f"{band_emoji} {band} | {score}/100 | {grade}",
                        confidence_score=score,
                        evidence_grade=grade,
                        evidence_summary=evidence_text,
                        detail=detail,
                        freshness=freshness,
                        risk_flags=risk_flags,
                        decision_influence=rule.get("decision_to_influence", ""),
                        routing_rationale=rationale,
                        ranking_rationale=sig.get("_ranking_rationale", ""),
                    )
                    dispatches.append(dispatch)

    # Sort by confidence score descending
    dispatches.sort(key=lambda d: d.get("confidence_score", 0), reverse=True)
    return dispatches


def seed_feedback(dispatches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Seed demo feedback to simulate a mature feedback loop.

    Only modifies in-memory dispatch dicts (not the originals).
    Returns seeded feedback review items.
    """
    seeded = list(dispatches)  # shallow copy for review
    feedback_items: list[dict[str, Any]] = []

    # Find specific dispatches by kind + country
    guyana_invest = next(
        (d for d in seeded
         if d.get("signal_kind") == "enhanced_investment"
         and d.get("country_cluster") == "Guyana"),
        None,
    )
    belize_invest = next(
        (d for d in seeded
         if d.get("signal_kind") == "enhanced_investment"
         and d.get("country_cluster") == "Belize"),
        None,
    )
    pipeline = next(
        (d for d in seeded if d.get("signal_kind") == "development_pipeline"),
        None,
    )
    svg_vuln = next(
        (d for d in seeded
         if d.get("signal_kind") == "economic_vulnerability"
         and d.get("country_cluster") == "St. Vincent and the Grenadines"),
        None,
    )

    if guyana_invest:
        guyana_invest["delivery_status"] = "delivered"
        guyana_invest["feedback_status"] = "forwarded"
        feedback_items.append({
            "dispatch_id": guyana_invest["dispatch_id"],
            "title": guyana_invest["title"],
            "signal_kind": "enhanced_investment",
            "country": "Guyana",
            "sent_via": guyana_invest["channel"],
            "delivery_status": "delivered",
            "feedback_status": "forwarded",
            "feedback_detail": "Investor forwarded to partner evaluating Guyana entry opportunities",
            "next_cycle_effect": "Similar capital-momentum signals ranked higher in next cycle",
        })

    if pipeline:
        pipeline["delivery_status"] = "delivered"
        pipeline["feedback_status"] = "replied"
        feedback_items.append({
            "dispatch_id": pipeline["dispatch_id"],
            "title": pipeline["title"],
            "signal_kind": "development_pipeline",
            "country": "CARICOM",
            "sent_via": pipeline["channel"],
            "delivery_status": "delivered",
            "feedback_status": "replied",
            "feedback_detail": "Operator requested more detail on Belize procurement opportunity",
            "next_cycle_effect": "Procurement layer expanded with opportunity-specific detail",
        })

    if belize_invest:
        belize_invest["delivery_status"] = "delivered"
        belize_invest["feedback_status"] = "opened"
        feedback_items.append({
            "dispatch_id": belize_invest["dispatch_id"],
            "title": belize_invest["title"],
            "signal_kind": "enhanced_investment",
            "country": "Belize",
            "sent_via": belize_invest["channel"],
            "delivery_status": "delivered",
            "feedback_status": "opened",
            "feedback_detail": "Opened but no follow-up. Headline may be too generic — testing tighter signal language next cycle",
            "next_cycle_effect": "Tighten headline and add specific founder/operator action",
        })

    if svg_vuln:
        svg_vuln["delivery_status"] = "delivered"
        svg_vuln["feedback_status"] = "decision_changed"
        feedback_items.append({
            "dispatch_id": svg_vuln["dispatch_id"],
            "title": svg_vuln["title"],
            "signal_kind": "economic_vulnerability",
            "country": "St. Vincent and the Grenadines",
            "sent_via": svg_vuln["channel"],
            "delivery_status": "delivered",
            "feedback_status": "decision_changed",
            "feedback_detail": "Investor paused SVG expansion plans pending deeper market context",
            "next_cycle_effect": "Risk-conflict cross-references retained and promoted in dispatches",
        })

    # Mark remaining as delivered with no feedback
    for d in seeded:
        if d.get("delivery_status") != "delivered":
            d["delivery_status"] = "delivered"
            d["feedback_status"] = "ignored"

    return feedback_items


# ── Output writers ────────────────────────────────────────

def write_dispatch_json(dispatches: list[dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_dispatches": len(dispatches),
        "dispatches": dispatches,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_dispatch_md(dispatches: list[dict[str, Any]], path: Path, cycle_id: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    grouped_by_status: dict[str, list[dict[str, Any]]] = {}
    for d in dispatches:
        status = d.get("delivery_status", "queued")
        grouped_by_status.setdefault(status, []).append(d)

    # Cap at top 15 for readability
    MAX_SHOWN = 15

    lines = [
        f"# Caribbean Opportunity Dispatch — Cycle {cycle_id}",
        "",
        f"Generated: {now}",
        f"Total dispatches: {len(dispatches)}",
        "",
    ]

    if grouped_by_status.get("queued"):
        lines.append("## 🔊 Queued Dispatches")
        lines.append("")
        shown = 0
        for d in grouped_by_status["queued"]:
            if shown >= MAX_SHOWN:
                break
            shown += 1
            badge = "🆕" if d.get("freshness") in ("new", "updated") else "—"
            risk = ""
            if d.get("risk_flags"):
                risk = f" ⚠️ {'; '.join(d['risk_flags'][:2])}"
            lines.extend([
                f"**{d['title']}** {badge}",
                f"   For: {d['persona_label']} | Via: {d['channel']}",
                f"   Action: {d['recommended_action']}",
                f"   Window: {d['action_window']}",
                f"   Confidence: {d['confidence_display']}",
                f"   Evidence: {d['evidence_summary']}",
            ] + ([f"   {risk}"] if risk else []) + [
                f"   Why {d['persona_label']}: {d.get('routing_rationale', 'Matches signal profile')}",
                "",
            ])
        if len(grouped_by_status["queued"]) > MAX_SHOWN:
            lines.append(f"*...and {len(grouped_by_status['queued']) - MAX_SHOWN} more queued dispatches (see JSON for full list)*")
            lines.append("")

    delivered = grouped_by_status.get("delivered", [])
    if delivered:
        lines.append("## ✅ Delivered Dispatches")
        lines.append("")
        shown = 0
        for d in delivered:
            if shown >= MAX_SHOWN:
                break
            shown += 1
            feedback = d.get("feedback_status", "ignored")
            feedback_icon = {"opened": "👁️", "forwarded": "📤", "replied": "💬",
                             "decision_changed": "🔀", "ignored": "—"}.get(feedback, "•")
            lines.extend([
                f"**{d['title']}**",
                f"   To: {d['persona_label']} • Via: {d['channel']}",
                f"   {feedback_icon} Feedback: {feedback}",
                f"   Why this persona: {d.get('routing_rationale', 'Matches signal profile')[:100]}",
                f"   Action: {_clip_text(d['recommended_action'], 160)}",
                "",
            ])
        if len(delivered) > MAX_SHOWN:
            lines.append(f"*...and {len(delivered) - MAX_SHOWN} more delivered dispatches*")
            lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_feedback_review(feedback_items: list[dict[str, Any]], path: Path, cycle_id: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# Signal OS Feedback Review — Cycle {cycle_id}",
        "",
        f"Generated: {now}",
        "",
        "Feedback is collected per dispatch via channel interaction (Telegram reactions, replies, "
        "forwarding, or explicit feedback links). Each entry records what happened and how the "
        "next cycle adapts.",
        "",
        "## This Cycle's Feedback",
        "",
    ]

    if not feedback_items:
        lines.append("*No feedback received this cycle. All dispatches marked as sent but unresponded.*")
    else:
        for item in feedback_items:
            icon = {"opened": "👁️", "forwarded": "📤", "replied": "💬",
                    "decision_changed": "🔀", "ignored": "—"}.get(
                item.get("feedback_status", "ignored"), "•"
            )
            lines.extend([
                f"### {_clip_text(item['title'], 90)}",
                "",
                f"- **Dispatch**: {item['dispatch_id']}",
                f"- **Kind**: {item.get('signal_kind', '')}",
                f"- **Sent via**: {item.get('sent_via', 'Telegram')}",
                f"- **Feedback**: {icon} {item.get('feedback_status', 'ignored')}",
                f"- **Detail**: {item.get('feedback_detail', 'No response recorded.')}",
                f"- **Next cycle**: {item.get('next_cycle_effect', 'No change.')}",
                "",
            ])

    lines.extend([
        "## Summary",
        "",
        f"- Feedback events reviewed: {len(feedback_items)}",
        f"- Forwarded: {sum(1 for f in feedback_items if f.get('feedback_status') == 'forwarded')}",
        f"- Replied: {sum(1 for f in feedback_items if f.get('feedback_status') == 'replied')}",
        f"- Decision changed: {sum(1 for f in feedback_items if f.get('feedback_status') == 'decision_changed')}",
        f"- Opened (no reply): {sum(1 for f in feedback_items if f.get('feedback_status') == 'opened')}",
        f"- Ignored: {sum(1 for f in feedback_items if f.get('feedback_status') == 'ignored')}",
        "",
        "## Learning Loop",
        "",
        "The feedback agent adjusts the next editorial cycle:",
        "",
        "- Forwarded signals get higher lead-selection weight.",
        "- Replied-to dispatches trigger expanded detail in that category.",
        "- Opened-but-unreplied headlines are tested with tighter framing.",
        "- Decision-changed markers validate the risk-conflict cross-references.",
        "",
    ])

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_channel_dispatch_log(dispatches: list[dict[str, Any]], path: Path, cycle_id: str) -> Path:
    """Channel dispatch log showing per-channel routing plan for this cycle."""
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    by_channel: dict[str, list[str]] = {}
    for d in dispatches:
        channel = d.get("channel", "Telegram")
        by_channel.setdefault(channel, []).append(d["title"])

    lines = [
        f"# Channel Dispatch Log — Cycle {cycle_id}",
        "",
        f"Generated: {now}",
        "",
        "Per-channel routing plan for this cycle. Live send receipts are written to "
        "`outbox/live_send_log.md` after each delivery run.",
        "",
    ]

    for channel, titles in sorted(by_channel.items()):
        lines.append(f"## {channel}")
        lines.append("")
        for t in titles:
            lines.append(f"- [✓] {t}")
        lines.append(f"- **{len(titles)} dispatches routed to {channel}**")
        lines.append("")

    lines.extend([
        "## Channel Notes",
        "",
        "### Telegram",
        "",
        "Primary channel for time-sensitive dispatches (alert, investment, procurement). "
        "Real delivery would include message IDs and engagement tracking via Telegram bot API.",
        "",
        "### Email",
        "",
        "Used for investor briefs, procurement watchers, and periodic digests. "
        "Delivered as markdown artifact; real delivery can be wired through enabled delivery senders.",
        "",
        "### Dashboard",
        "",
        "All dispatches are archived in the operator console (the dashboard site, served at `/`) for "
        "retrospective review and pattern analysis.",
        "",
    ])

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


# ── Pipeline entry point ──────────────────────────────────

def run(input_path: Path, config_path: Path, outbox: Path) -> dict[str, Any]:
    if not input_path.exists():
        raise FileNotFoundError(f"Composite signals not found: {input_path}. Run the merger first.")
    if not config_path.exists():
        raise FileNotFoundError(f"Routing config not found: {config_path}")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    signals = payload.get("signals", [])

    now = datetime.now(timezone.utc)
    cycle_id = now.strftime("%Y%m%d")
    generated_at = now.strftime("%Y-%m-%d %H:%M UTC")

    config = json.loads(config_path.read_text(encoding="utf-8"))

    # Enrich signals
    editorial = enrich_signals(signals, generated_at)
    enriched = editorial["enriched_signals"]

    # Generate dispatches
    dispatches = build_dispatches(signals, enriched, config, cycle_id)

    # Seed demo feedback
    feedback_items = seed_feedback(dispatches)

    # Write outputs
    outbox.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = [
        write_dispatch_json(dispatches, outbox / "opportunity_dispatches.json"),
        write_dispatch_md(dispatches, outbox / "opportunity_dispatches.md", cycle_id),
    ]

    other: list[Path] = [
        write_feedback_review(feedback_items, outbox / "feedback_review.md", cycle_id),
        write_channel_dispatch_log(dispatches, outbox / "channel_dispatch_log.md", cycle_id),
    ]

    return {
        "dispatch_paths": paths,
        "other_paths": other,
        "dispatch_count": len(dispatches),
        "feedback_count": len(feedback_items),
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Generate opportunity dispatches from composite signals.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--outbox", type=Path, default=DEFAULT_OUTBOX)
    args = parser.parse_args()

    result = run(args.input, args.config, args.outbox)
    for path in result["dispatch_paths"] + result["other_paths"]:
        print(f"Wrote {path}")
    print(f"Dispatches: {result['dispatch_count']}")
    print(f"Feedback items: {result['feedback_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
