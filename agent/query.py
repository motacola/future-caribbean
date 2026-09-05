#!/usr/bin/env python3
"""Headless deterministic query layer for Dispatch Desk artifacts.

This is intentionally stdlib-only and non-LLM. It gives the web analyst rail,
CLI, and future API one shared source of truth for explanations and drilldowns.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DESK_JSON = ROOT / "outbox" / "dispatch_desk.json"


def load_desk(path: Path = DESK_JSON) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run bash run_pipeline.sh first.")
    return json.loads(path.read_text(encoding="utf-8"))


def clean(text: Any) -> str:
    return " ".join(str(text or "").split())


def clip(text: Any, limit: int = 180) -> str:
    value = clean(text)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rsplit(" ", 1)[0].rstrip(".,;:") + "…"


def artifact_citation(*names: str) -> str:
    return "Sources: " + ", ".join(f"`{name}`" for name in names)


def lead_cluster(desk: dict[str, Any]) -> dict[str, Any] | None:
    clusters = desk.get("clusters", []) or []
    return clusters[0] if clusters else None


def explain_lead(desk: dict[str, Any]) -> str:
    cluster = lead_cluster(desk)
    if not cluster:
        return "No decision clusters are available. Run the pipeline first.\n\n" + artifact_citation("outbox/dispatch_desk.json")

    routes = cluster.get("personas", []) or []
    route_lines = []
    for route in routes[:4]:
        route_lines.append(
            f"- {route.get('persona', 'Persona')} via {route.get('channel', 'channel')}: "
            f"{clip(route.get('action', 'Review dispatch.'), 130)} "
            f"[{route.get('dispatch_id', 'no-id')}, feedback={route.get('feedback_status', 'awaiting')}]"
        )

    risks = cluster.get("risk_flags", []) or []
    risk_line = ""
    if risks:
        risk_line = "\nRisk flags: " + "; ".join(str(r) for r in risks[:3])

    return "\n".join([
        f"Lead signal: {cluster.get('title', 'Untitled cluster')}",
        f"Decision: {cluster.get('decision', 'No decision recorded.')}",
        f"Evidence: {cluster.get('evidence', 'No evidence recorded.')} ({cluster.get('evidence_grade', 'grade n/a')})",
        f"Confidence: {cluster.get('confidence_score', 0)}/100; freshness={cluster.get('freshness', 'unknown')}",
        f"Feedback: {cluster.get('feedback_summary', 'No feedback summary.')}",
        risk_line.strip(),
        "",
        "Persona routes:",
        *route_lines,
        "",
        artifact_citation("outbox/dispatch_desk.json", "outbox/opportunity_dispatches.json"),
    ]).replace("\n\n\n", "\n\n")


def routes_for_persona(desk: dict[str, Any], persona_query: str) -> str:
    q = persona_query.lower()
    rows: list[str] = []
    for cluster in desk.get("clusters", []) or []:
        for route in cluster.get("personas", []) or []:
            persona = str(route.get("persona", ""))
            if q in persona.lower() or ("investor" in q and "investor" in persona.lower()):
                rows.append(
                    f"- {cluster.get('title', 'Untitled')}: {clip(route.get('action'), 145)} "
                    f"[{route.get('dispatch_id', 'no-id')}, {route.get('feedback_status', 'awaiting')}]"
                )
    if not rows:
        return f"No routes matched persona query `{persona_query}`.\n\n" + artifact_citation("outbox/dispatch_desk.json")
    return "\n".join([f"Routes matching `{persona_query}`:", "", *rows[:10], "", artifact_citation("outbox/dispatch_desk.json")])


def drill_country(desk: dict[str, Any], country: str) -> str:
    q = country.lower()
    rows: list[str] = []
    for cluster in desk.get("clusters", []) or []:
        title = str(cluster.get("title", ""))
        cluster_country = str(cluster.get("country_cluster", ""))
        if q in title.lower() or q in cluster_country.lower():
            rows.append(
                f"- {title}: {cluster.get('decision', 'No decision recorded.')} "
                f"({cluster.get('confidence_score', 0)}/100, {cluster.get('evidence_grade', 'grade n/a')})"
            )
    if not rows:
        return f"No country drilldown matched `{country}`.\n\n" + artifact_citation("outbox/dispatch_desk.json")
    return "\n".join([f"Country drilldown: {country}", "", *rows[:10], "", artifact_citation("outbox/dispatch_desk.json")])


def what_changed(desk: dict[str, Any]) -> str:
    clusters = desk.get("clusters", []) or []
    freshness = {}
    for cluster in clusters:
        key = cluster.get("freshness", "unknown")
        freshness[key] = freshness.get(key, 0) + 1
    freshness_line = ", ".join(f"{k}: {v}" for k, v in sorted(freshness.items())) or "no freshness data"
    boosts = desk.get("boost_lines", []) or []
    boost_lines = [f"- {line}" for line in boosts[:6]] or ["- No active feedback boosts this cycle."]
    return "\n".join([
        f"Cycle {desk.get('cycle_id', 'unknown')} changed summary:",
        f"- {desk.get('cluster_count', len(clusters))} decision clusters from {desk.get('dispatch_count', 0)} persona routes",
        f"- Freshness mix: {freshness_line}",
        "- Feedback-adjusted priority:",
        *boost_lines,
        "",
        artifact_citation("outbox/dispatch_desk.json", "data/feedback/current_boosts.json"),
    ])


def draft_note(desk: dict[str, Any], country_or_persona: str) -> str:
    q = country_or_persona.lower()
    chosen = None
    chosen_route = None
    for cluster in desk.get("clusters", []) or []:
        if q in str(cluster.get("title", "")).lower() or q in str(cluster.get("country_cluster", "")).lower():
            chosen = cluster
            for route in cluster.get("personas", []) or []:
                if "investor" in str(route.get("persona", "")).lower():
                    chosen_route = route
                    break
            chosen_route = chosen_route or (cluster.get("personas", []) or [None])[0]
            break
    if not chosen:
        chosen = lead_cluster(desk)
        chosen_route = (chosen.get("personas", []) or [None])[0] if chosen else None
    if not chosen or not chosen_route:
        return "No dispatch available to draft from.\n\n" + artifact_citation("outbox/dispatch_desk.json")

    country = chosen.get("country_cluster", "the region")
    title = chosen.get("title", "current signal")
    action = chosen_route.get("action", "review the signal and validate locally")
    return "\n".join([
        f"Draft note for {country}:",
        "",
        f"Subject: {country} signal worth reviewing this cycle",
        "",
        f"A current Abeng signal flagged {title}.",
        f"Evidence: {chosen.get('evidence', 'Evidence recorded in Dispatch Desk')} ({chosen.get('evidence_grade', 'grade n/a')}).",
        f"Suggested next step: {action}",
        "",
        "I would treat this as a diligence trigger, not an investment recommendation: validate sector fit, local operator quality, and timing before acting.",
        "",
        artifact_citation("outbox/dispatch_desk.json"),
    ])


def ask(question: str, desk: dict[str, Any]) -> str:
    q = question.lower().strip()
    if not q:
        return "Ask about a country, persona, lead signal, feedback changes, or draft note."
    if any(term in q for term in ["lead", "first", "why is", "ranked first", "top signal"]):
        return explain_lead(desk)
    if any(term in q for term in ["what changed", "changed this cycle", "feedback", "boost", "downrank", "uprank"]):
        return what_changed(desk)
    if "investor" in q:
        if "draft" in q or "note" in q or "message" in q:
            country_match = re.search(r"(?:draft|note|message).*?([A-Z][a-zA-Z .-]+)", question)
            target = country_match.group(1) if country_match else "investor"
            return draft_note(desk, target)
        return routes_for_persona(desk, "investor")
    if "procurement" in q:
        return routes_for_persona(desk, "procurement")
    if "founder" in q or "operator" in q:
        return routes_for_persona(desk, "operator")
    country_terms = ["guyana", "belize", "suriname", "barbados", "caricom", "vincent", "antigua", "kitts"]
    for country in country_terms:
        if country in q:
            if "draft" in q or "note" in q or "message" in q:
                return draft_note(desk, country)
            return drill_country(desk, country)
    return "I can answer deterministic Dispatch Desk questions right now. Try: `explain lead`, `show investor actions`, `what changed this cycle`, `Belize drilldown`, or `draft Guyana investor note`.\n\n" + artifact_citation("outbox/dispatch_desk.json")


def feedback_command(dispatch_id: str, status: str, note: str = "") -> str:
    safe_note = note.replace('"', "'")
    return f'python3 packagers/feedback_intake.py --dispatch-id {dispatch_id} --status {status} --note "{safe_note}"'


def main() -> int:
    parser = argparse.ArgumentParser(description="Query Dispatch Desk artifacts deterministically.")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("explain-lead")
    ask_parser = sub.add_parser("ask")
    ask_parser.add_argument("question", nargs="+")
    persona_parser = sub.add_parser("persona")
    persona_parser.add_argument("persona")
    country_parser = sub.add_parser("country")
    country_parser.add_argument("country")
    sub.add_parser("what-changed")
    draft_parser = sub.add_parser("draft")
    draft_parser.add_argument("target")
    feedback_parser = sub.add_parser("feedback-command")
    feedback_parser.add_argument("dispatch_id")
    feedback_parser.add_argument("status")
    feedback_parser.add_argument("--note", default="")

    args = parser.parse_args()
    desk = load_desk()
    if args.cmd == "explain-lead":
        print(explain_lead(desk))
    elif args.cmd == "ask":
        print(ask(" ".join(args.question), desk))
    elif args.cmd == "persona":
        print(routes_for_persona(desk, args.persona))
    elif args.cmd == "country":
        print(drill_country(desk, args.country))
    elif args.cmd == "what-changed":
        print(what_changed(desk))
    elif args.cmd == "draft":
        print(draft_note(desk, args.target))
    elif args.cmd == "feedback-command":
        print(feedback_command(args.dispatch_id, args.status, args.note))
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
