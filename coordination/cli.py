#!/usr/bin/env python3
"""Coordination CLI — operator-facing commands for the closed loop.

Usage (run from repo root):
  python3 coordination/cli.py run
  python3 coordination/cli.py state [--id ID]
  python3 coordination/cli.py submit-evidence --id ID --summary "..." --source "..." [--country BB]
  python3 coordination/cli.py verify --id ID
  python3 coordination/cli.py submit-outcome --id ID --type intro_accepted|supplier_validated|blocked_logistics [--note "..."]

Outcomes feed back into scoring: a validated supplier or accepted intro
nudges the opportunity score up; a logistics block keeps the gap
open but records WHY (honest, not hidden).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_mod():
    try:
        from coordination import interventions, engine
    except ImportError:
        import interventions  # type: ignore
        import engine  # type: ignore
        sys.modules.setdefault("coordination.interventions", interventions)
        sys.modules.setdefault("coordination.engine", engine)
    return interventions, engine


def cmd_run(_args: argparse.Namespace) -> int:
    _, engine = _load_mod()
    graph, opportunities = engine.run(ROOT)
    print(f"graph: {graph['counts']['nodes']} nodes, {graph['counts']['edges']} edges")
    print(f"opportunities: {opportunities['count']} candidates, {opportunities['screened_out_count']} screened out")
    print(f"interventions_persisted: {opportunities['interventions_persisted']}")
    return 0


def cmd_state(args: argparse.Namespace) -> int:
    interventions, _ = _load_mod()
    state = interventions.get_state(ROOT)
    if args.id:
        entry = state["interventions"].get(args.id)
        if not entry:
            print(f"unknown intervention: {args.id}", file=sys.stderr)
            return 2
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return 0
    summary = {
        "interventions": len(state["interventions"]),
        "campaigns": len(state["campaigns"]),
        "by_status": _count_by(state["interventions"], "status"),
        "with_outcomes": sum(
            1 for e in state["interventions"].values() if e.get("outcomes")
        ),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def _count_by(items: dict, key: str) -> dict:
    out: dict[str, int] = {}
    for e in items.values():
        out[e.get(key, "?")] = out.get(e.get(key, "?"), 0) + 1
    return out


def cmd_submit_evidence(args: argparse.Namespace) -> int:
    interventions, _ = _load_mod()
    entry = interventions.add_evidence(
        args.id, args.summary, args.source, args.country, root=ROOT
    )
    print(f"evidence added to {args.id} → status: {entry['status']}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    interventions, _ = _load_mod()
    record = interventions.verify(args.id, root=ROOT)
    changes = record.get("score_changes", {})
    moved = {k: v for k, v in changes.items() if v.get("before") != v.get("after")}
    print(f"verified {args.id}")
    if record.get("verified_edge"):
        print(f"  edge pushed: {record['verified_edge']}")
    if moved:
        for opp_id, delta in moved.items():
            print(f"  score {opp_id}: {delta['before']} → {delta['after']}")
    else:
        print("  no score changes")
    return 0


def cmd_submit_outcome(args: argparse.Namespace) -> int:
    interventions, _ = _load_mod()
    entry = interventions.submit_outcome(args.id, args.type, args.note or "", root=ROOT)
    print(f"outcome '{args.type}' recorded on {args.id}")
    if entry.get("blocked_reason"):
        print(f"  blocked: {entry['blocked_reason']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Coordination graph operator CLI")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="rebuild graph + opportunities").set_defaults(func=cmd_run)

    st = sub.add_parser("state", help="show intervention state")
    st.add_argument("--id", help="intervention id")
    st.set_defaults(func=cmd_state)

    se = sub.add_parser("submit-evidence", help="attach cited evidence")
    se.add_argument("--id", required=True)
    se.add_argument("--summary", required=True)
    se.add_argument("--source", required=True)
    se.add_argument("--country", default=None)
    se.set_defaults(func=cmd_submit_evidence)

    ve = sub.add_parser("verify", help="verify an intervention, push edge, recompute scores")
    ve.add_argument("--id", required=True)
    ve.set_defaults(func=cmd_verify)

    oc = sub.add_parser("submit-outcome", help="record an operator coordination outcome")
    oc.add_argument("--id", required=True)
    oc.add_argument("--type", required=True,
                     choices=["intro_accepted", "supplier_validated", "blocked_logistics"])
    oc.add_argument("--note", default="")
    oc.set_defaults(func=cmd_submit_outcome)

    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
