#!/usr/bin/env python3
"""signalctl — command-line control for the Signal Fabric engine.

A thin, dependency-free CLI over the same engine the web UI drives. Lets you
run the pipeline, inspect live instances and signals, render a dispatch the
way a recipient would receive it, read the reasoning agent's synthesis, and
send to a channel — all from a terminal.

Usage:
    python3 cli/signalctl.py <command> [options]

Commands:
    status                         Source health, cycle, instances, outcomes
    domains                        List engine instances (live + blueprints)
    signals [--domain D] [-n N]    Current signals for an instance
    preview [--domain D] [--persona P] [--channel C]
                                   Render a dispatch as a recipient sees it
    reason                         Cross-signal synthesis from the reasoning agent
    run                            Run one full pipeline cycle
    send [--channel telegram] [--live]
                                   Send the current digest (dry-run by default)
    ask <question>                 Ask the desk a deterministic question (no server needed)
    coordinator status             Intervention states and operator campaigns
    coordinator submit-evidence --id I --summary S --source SRC [--country C]
                                   Attach cited evidence to an intervention
    coordinator verify --id I      Verify an intervention, update graph, recompute scores

Examples:
    python3 cli/signalctl.py status
    python3 cli/signalctl.py signals --domain climate
    python3 cli/signalctl.py preview --persona investor --channel telegram
    python3 cli/signalctl.py preview --domain climate --persona policy
    python3 cli/signalctl.py ask "explain the lead signal"
    python3 cli/signalctl.py ask "what changed this cycle"
    python3 cli/signalctl.py ask "draft a note for Guyana"
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── tiny ANSI helpers (no deps) ─────────────────────────────────
_USE_COLOR = sys.stdout.isatty()
def _c(s: str, code: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _USE_COLOR else s
def bold(s): return _c(s, "1")
def teal(s): return _c(s, "36")
def gold(s): return _c(s, "33")
def green(s): return _c(s, "32")
def dim(s): return _c(s, "2")
def red(s): return _c(s, "31")


def _read(rel: str) -> dict:
    p = ROOT / rel
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# ── commands ────────────────────────────────────────────────────

def cmd_status(args) -> int:
    src_keys = [
        ("World Bank", "world_bank"), ("IDB", "idb"), ("NOAA", "noaa"),
        ("NDBC", "ndbc"), ("CARICOM/CDB", "tier2"),
    ]
    print(bold("\nSignal Fabric — status\n"))
    live = 0
    for name, key in src_keys:
        ok = (ROOT / "data" / key / "latest.json").exists()
        if ok:
            live += 1
        dot = green("●") if ok else dim("○")
        print(f"  {dot} {name:<14} {'live' if ok else 'offline'}")
    print(f"\n  Sources live : {live}/5 dirs")

    desk = _read("outbox/dispatch_desk.json")
    clim = _read("outbox/climate_desk.json")
    print(f"  Cycle        : {desk.get('cycle_id', '—')}")
    print(f"  Generated    : {desk.get('generated_at', '—')}")
    print(f"  Instances    : {green('2 live')} (Caribbean economic, Climate hazard)")
    print(f"  Dispatches   : {desk.get('dispatch_count', 0)} economic · "
          f"{clim.get('dispatch_count', 0)} climate")

    fb = _read("data/feedback/state.json").get("history", [])
    counts: dict[str, int] = {}
    for e in fb:
        s = e.get("feedback_status", "?")
        counts[s] = counts.get(s, 0) + 1
    if counts:
        actioned = sum(v for k, v in counts.items() if k != "ignored")
        print(f"  Outcomes     : {actioned} actioned "
              f"({counts.get('decision_changed', 0)} changed a decision, "
              f"{counts.get('replied', 0)} replied, {counts.get('forwarded', 0)} forwarded)")
    print()
    return 0


def cmd_domains(args) -> int:
    from domains.registry import load_all, summarise
    domains, errors = load_all(validate=True)
    print(bold(f"\nSignal Fabric — {len(domains)} domain(s)\n"))
    for d in domains:
        s = summarise(d)
        c = s["counts"]
        tag = green("● LIVE     ") if s["status"] == "live" else dim("○ blueprint")
        print(f"  {tag}  {bold(s['name'])}")
        print(dim(f"               {c['sources_wired']}/{c['sources']} sources wired · "
                  f"{c['signals']} signal rules · {c['recipients']} recipient roles"))
    if errors:
        print(red("\n  validation issues:"))
        for e in errors:
            print(red(f"   ✗ {e}"))
    print()
    return 0


def _desk_for(domain: str) -> dict:
    return _read("outbox/climate_desk.json" if domain == "climate" else "outbox/dispatch_desk.json")


def cmd_signals(args) -> int:
    desk = _desk_for(args.domain)
    clusters = desk.get("clusters", [])
    if not clusters:
        print(red(f"No signals for '{args.domain}'. Run: signalctl run"))
        return 1
    label = "Climate hazard" if args.domain == "climate" else "Caribbean economic"
    print(bold(f"\n{label} signals — cycle {desk.get('cycle_id', '—')}\n"))
    for c in clusters[:args.limit]:
        score = c.get("confidence_score", 0)
        fresh = c.get("freshness", "")
        fresh_s = f" {gold('['+fresh+']')}" if fresh else ""
        print(f"  {teal(f'{score:>3}')} {bold(c.get('title', '')[:72])}{fresh_s}")
        print(dim(f"      {c.get('country_cluster', '')} · {c.get('evidence', '')[:80]}"))
        if c.get("risk_flags"):
            print(red(f"      ⚠ {c['risk_flags'][0][:72]}"))
    print()
    return 0


def cmd_preview(args) -> int:
    desk = _desk_for(args.domain)
    clusters = desk.get("clusters", [])
    if not clusters:
        print(red(f"No signals for '{args.domain}'. Run: signalctl run"))
        return 1
    cluster = clusters[0]
    persona_terms = {
        "investor": ["investor", "diaspora", "insurer"],
        "founder": ["founder", "operator", "operations", "resilience"],
        "policy": ["policy", "media", "planner"],
        "diaspora": ["diaspora", "insurer"],
    }.get(args.persona, [args.persona])
    rec = next((p for p in cluster.get("personas", [])
                if any(t in p.get("persona", "").lower() for t in persona_terms)),
               (cluster.get("personas") or [{}])[0])

    country = cluster.get("country_cluster", "Caribbean")
    evidence = cluster.get("evidence", "")
    evidence = re.sub(rf"^\s*{re.escape(country)}\s*:\s*", "", evidence)
    evidence = re.sub(rf"\s*:\s*{re.escape(country)}\s*\.?\s*$", "", evidence)
    evidence = re.sub(r"\bWB\b", "World Bank", evidence)
    evidence = re.sub(r"FDI surge detected", "FDI inflows rising", evidence)
    evidence = re.sub(r"detected:\s*", "", evidence)
    evidence = re.sub(r"FDI surge", "FDI movement", evidence).strip()
    grade = (cluster.get("evidence_grade", "C") or "C")[0].upper()
    conf = {"A": "High confidence", "B": "Moderate confidence", "C": "Early signal"}.get(grade, "Early signal")
    action = (rec.get("action") or cluster.get("decision", ""))[:200]
    role = rec.get("persona", args.persona.title())
    is_clim = args.domain == "climate"
    head = "Caribbean Hazard Signal" if is_clim else "Caribbean Opportunity Signal"
    disc = ("Decision-support signal. Follow official emergency directives."
            if is_clim else "Screening signal only. Not investment advice.")

    print()
    print(dim(f"  ┌─ {args.channel.upper()} · {role} " + "─" * max(0, 40 - len(role))))
    print(f"  │ {bold(head)}")
    print(f"  │ {teal(country)} — {conf}")
    print("  │")
    for line in _wrap(evidence, 60):
        print(f"  │ {line}")
    print("  │")
    print(f"  │ {bold('What to do:')}")
    for line in _wrap(action, 60):
        print(f"  │ {line}")
    if cluster.get("risk_flags"):
        print(f"  │ {red('⚠ ' + cluster['risk_flags'][0][:58])}")
    print(f"  │ {dim(disc)}")
    print(dim("  └" + "─" * 48))
    print()
    return 0


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def cmd_reason(args) -> int:
    r = _read("outbox/reasoning.json")
    if not r:
        print(red("No synthesis yet. Run: signalctl run"))
        return 1
    eng = r.get("engine", "?")
    badge = teal("⚡ " + (r.get("model") or "LLM")) if eng == "llm" else dim("deterministic")
    print(bold("\nReasoning agent — cross-signal synthesis  ") + badge + "\n")
    for line in _wrap(r.get("thesis", ""), 76):
        print(f"  {line}")
    if r.get("connections"):
        print()
        for c in r["connections"]:
            print(gold("  → ") + c)
    print()
    return 0


def cmd_run(args) -> int:
    print(bold("Running one pipeline cycle…\n"))
    rc = subprocess.run(["bash", "run_pipeline.sh"], cwd=str(ROOT)).returncode
    print(green("\n✓ cycle complete") if rc == 0 else red(f"\n✗ exit {rc}"))
    return rc


def cmd_send(args) -> int:
    script = ROOT / "distributors" / "telegram_sender.py"
    if not script.exists():
        print(red("telegram_sender.py not found"))
        return 1
    flags = [] if args.live else ["--dry-run"]
    print(bold(f"Sending via {args.channel} ({'LIVE' if args.live else 'dry-run'})...\n"))
    return subprocess.run(["python3", str(script), *flags], cwd=str(ROOT)).returncode


def cmd_coordinator_status(args) -> int:
    from coordination.interventions import get_state, ACTIVE_STATES
    state = get_state()
    interventions = state.get("interventions", {})
    campaigns = state.get("campaigns", {})
    if not interventions:
        print(dim("No interventions on record. Run: python3 coordination/engine.py"))
        return 0
    by_status: dict[str, list[dict]] = {}
    for entry in interventions.values():
        by_status.setdefault(entry.get("status", "proposed"), []).append(entry)
    print(bold("\nCoordination interventions\n"))
    for status in ("proposed", "evidence_requested", "evidence_received", "verified", "rejected", "expired"):
        entries = by_status.get(status)
        if not entries:
            continue
        color = green if status == "verified" else (gold if status in ACTIVE_STATES else dim)
        print(color(f"  {status} ({len(entries)})"))
        for entry in sorted(entries, key=lambda item: item.get("id", "")):
            print(f"    {entry['id']}")
            print(dim(f"      owner: {entry.get('owner_persona')}  blocker: {entry.get('blocker')}  evidence: {len(entry.get('evidence', []))}"))
    if campaigns:
        print(bold("\nOperator campaigns\n"))
        for campaign in sorted(campaigns.values(), key=lambda item: (-item.get("active_count", 0), item.get("slug", ""))):
            print(f"  {campaign['slug']}")
            print(dim(f"      interventions: {campaign.get('intervention_count')}  active: {campaign.get('active_count')}  owner: {campaign.get('owner_persona')}"))
    print()
    return 0


def cmd_coordinator_submit_evidence(args) -> int:
    from coordination.interventions import add_evidence
    try:
        entry = add_evidence(args.id, args.summary, args.source, country=args.country)
    except (KeyError, ValueError) as exc:
        print(red(str(exc)))
        return 1
    print(green(f"Evidence recorded for {entry['id']} (status: {entry['status']})"))
    return 0


def cmd_coordinator_verify(args) -> int:
    from coordination.interventions import verify
    try:
        record = verify(args.id)
    except (KeyError, ValueError) as exc:
        print(red(str(exc)))
        return 1
    print(green(f"Verified {args.id}"))
    if record.get("verified_edge"):
        edge = record["verified_edge"]
        print(dim(f"  cited HAS_CAPABILITY edge: {edge['country']} -> {edge['capability']}"))
    changes = record.get("score_changes") or {}
    if changes:
        for opp_id, change in changes.items():
            print(f"  {opp_id}: {change['before']} -> {change['after']}")
    else:
        print(dim("  no opportunity score changes"))
    return 0


def cmd_ask(args) -> int:
    question = " ".join(args.question)
    desk = _read("outbox/dispatch_desk.json")
    if not desk:
        print(red("No dispatch desk found. Run: signalctl run"))
        return 1
    try:
        sys.path.insert(0, str(ROOT))
        from agent.query import ask
        answer = ask(question, desk)
        print()
        print(bold(f"Q: {question}"))
        print()
        print(answer)
        print()
        return 0
    except FileNotFoundError as exc:
        print(red(str(exc)))
        return 1
    except Exception as exc:
        print(red(f"Error: {exc}"))
        return 1


# ── arg parsing ─────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="signalctl", description="Command-line control for the Signal Fabric engine.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="source health, cycle, instances, outcomes").set_defaults(fn=cmd_status)
    sub.add_parser("domains", help="list engine instances").set_defaults(fn=cmd_domains)

    s = sub.add_parser("signals", help="current signals for an instance")
    s.add_argument("--domain", default="caribbean", choices=["caribbean", "climate"])
    s.add_argument("-n", "--limit", type=int, default=8)
    s.set_defaults(fn=cmd_signals)

    pv = sub.add_parser("preview", help="render a dispatch as a recipient sees it")
    pv.add_argument("--domain", default="caribbean", choices=["caribbean", "climate"])
    pv.add_argument("--persona", default="investor",
                    choices=["investor", "founder", "policy", "diaspora"])
    pv.add_argument("--channel", default="telegram",
                    choices=["telegram", "whatsapp", "email", "memo"])
    pv.set_defaults(fn=cmd_preview)

    sub.add_parser("reason", help="cross-signal synthesis").set_defaults(fn=cmd_reason)
    sub.add_parser("run", help="run one full pipeline cycle").set_defaults(fn=cmd_run)

    sd = sub.add_parser("send", help="send the current digest")
    sd.add_argument("--channel", default="telegram", choices=["telegram"])
    sd.add_argument("--live", action="store_true", help="send for real (default: dry-run)")
    sd.set_defaults(fn=cmd_send)

    aq = sub.add_parser("ask", help="ask the desk a deterministic question (no server needed)")
    aq.add_argument("question", nargs="+", help="question to ask (e.g., 'explain the lead signal')")
    aq.set_defaults(fn=cmd_ask)

    co = sub.add_parser("coordinator", help="coordination intervention lifecycle")
    co_sub = co.add_subparsers(dest="coordinator_cmd", required=True)
    co_sub.add_parser("status", help="intervention states and operator campaigns").set_defaults(fn=cmd_coordinator_status)
    ce = co_sub.add_parser("submit-evidence", help="attach cited evidence to an intervention")
    ce.add_argument("--id", required=True, help="intervention id (see coordinator status)")
    ce.add_argument("--summary", required=True, help="what the evidence shows")
    ce.add_argument("--source", required=True, help="where the evidence comes from")
    ce.add_argument("--country", default=None, help="regional node the evidence names (required to verify capability interventions)")
    ce.set_defaults(fn=cmd_coordinator_submit_evidence)
    cv = co_sub.add_parser("verify", help="verify an intervention, update the graph, recompute scores")
    cv.add_argument("--id", required=True, help="intervention id")
    cv.set_defaults(fn=cmd_coordinator_verify)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
