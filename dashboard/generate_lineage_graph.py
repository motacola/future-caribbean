#!/usr/bin/env python3
"""Generate Abeng data lineage graph using graphify.

Creates an interactive graph showing:
- 8 data sources
- 8 watchers
- Cross-source merger
- 14 composite signal types
- 11 personas/routes
- Key output artifacts
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH_OUT = ROOT / "dashboard" / "abeng-lineage.graphify.json"


def build_lineage_graph() -> dict:
    """Build the complete Abeng data lineage graph."""

    nodes = []
    edges = []

    # ── SOURCES ──
    sources = [
        {"id": "src_wb", "label": "World Bank", "type": "source", "description": "REST API · 5 indicators × 13 countries", "color": "#2676A8"},
        {"id": "src_idb", "label": "IDB Open Data", "type": "source", "description": "CKAN API · 99 Caribbean datasets", "color": "#2676A8"},
        {"id": "src_noaa", "label": "NOAA NWS", "type": "source", "description": "REST API · Weather alerts", "color": "#0D766E"},
        {"id": "src_ndbc", "label": "NDBC Buoys", "type": "source", "description": "Tabular text · 6 buoys", "color": "#0D766E"},
        {"id": "src_caricom", "label": "CARICOM Stats", "type": "source", "description": "WP REST API · 126 datasets", "color": "#B57A22"},
        {"id": "src_cdb", "label": "CDB", "type": "source", "description": "RSS · Procurement & evaluations", "color": "#B57A22"},
        {"id": "src_ccrif", "label": "CCRIF SPC", "type": "source", "description": "Parametric payouts (TC, EQ, rainfall)", "color": "#B94836"},
        {"id": "src_eccb", "label": "ECCB", "type": "source", "description": "Monetary stats (credit, deposits, NFA)", "color": "#B57A22"},
    ]

    # ── WATCHERS ──
    watchers = [
        {"id": "w_wb", "label": "World Bank\nPoller", "type": "watcher", "description": "5 indicators × 13 countries", "color": "#2676A8"},
        {"id": "w_idb", "label": "IDB CKAN\nPoller", "type": "watcher", "description": "99 datasets", "color": "#2676A8"},
        {"id": "w_tier2", "label": "Tier 2\nScraper", "type": "watcher", "description": "CARICOM WP API + CDB RSS", "color": "#B57A22"},
        {"id": "w_tenders", "label": "Tenders\nPoller", "type": "watcher", "description": "Guyana eProcure API", "color": "#2676A8"},
        {"id": "w_ccrif", "label": "CCRIF\nPoller", "type": "watcher", "description": "Parametric payouts scrape", "color": "#B94836"},
        {"id": "w_eccb", "label": "ECCB\nPoller", "type": "watcher", "description": "Monetary stats scrape", "color": "#B57A22"},
        {"id": "w_noaa", "label": "NOAA NWS\nPoller", "type": "watcher", "description": "Active weather alerts", "color": "#0D766E"},
        {"id": "w_ndbc", "label": "NDBC Buoy\nPoller", "type": "watcher", "description": "6 buoys wind/pressure", "color": "#0D766E"},
        {"id": "w_nhc", "label": "NHC Storm\nPoller", "type": "watcher", "description": "Tropical cyclone tracking", "color": "#B94836"},
    ]

    # ── MERGER ──
    merger = {
        "id": "merger",
        "label": "Cross-Source\nMerger",
        "type": "merger",
        "description": "Composite rules engine · 14 signal types",
        "color": "#18251F",
    }

    # ── COMPOSITE SIGNALS ──
    signals = [
        {"id": "sig_cyclone", "label": "🌀 Cyclone Risk", "type": "signal", "priority": "high", "color": "#B94836"},
        {"id": "sig_maritime", "label": "🚢 Maritime Hazard", "type": "signal", "priority": "medium", "color": "#B6C74E"},
        {"id": "sig_invest", "label": "💼 Investment Signal", "type": "signal", "priority": "medium", "color": "#2676A8"},
        {"id": "sig_enhanced", "label": "💎 Enhanced Investment", "type": "signal", "priority": "medium", "color": "#2676A8"},
        {"id": "sig_vuln", "label": "⚠️ Economic Vulnerability", "type": "signal", "priority": "medium", "color": "#B94836"},
        {"id": "sig_tourism", "label": "🏖️ Tourism Impact", "type": "signal", "priority": "low", "color": "#B6C74E"},
        {"id": "sig_food", "label": "🌾 Food Security", "type": "signal", "priority": "medium", "color": "#B6C74E"},
        {"id": "sig_dev", "label": "🏗️ Development Pipeline", "type": "signal", "priority": "medium", "color": "#B57A22"},
        {"id": "sig_supply", "label": "🔗 Supply Chain", "type": "signal", "priority": "medium", "color": "#B57A22"},
        {"id": "sig_ccrif", "label": "💰 CCRIF Payout", "type": "signal", "priority": "high", "color": "#B94836"},
        {"id": "sig_eccb_credit", "label": "🏦 ECCB Credit Surge", "type": "signal", "priority": "medium", "color": "#B57A22"},
        {"id": "sig_eccb_deposit", "label": "🏦 ECCB Deposit Growth", "type": "signal", "priority": "medium", "color": "#B57A22"},
        {"id": "sig_trop_dev", "label": "🌪️ Tropical Development", "type": "signal", "priority": "high", "color": "#B94836"},
        {"id": "sig_active_storm", "label": "🌀 Active Storm", "type": "signal", "priority": "high", "color": "#B94836"},
    ]

    # ── PERSONAS ──
    personas = [
        {"id": "p_diaspora", "label": "💼 Diaspora Investor", "type": "persona", "channel": "Email + Telegram", "color": "#2676A8"},
        {"id": "p_founder", "label": "🏭 Founder/Operator", "type": "persona", "channel": "Telegram", "color": "#2676A8"},
        {"id": "p_ecosystem", "label": "🌐 Ecosystem Builder", "type": "persona", "channel": "Telegram", "color": "#0D766E"},
        {"id": "p_regional", "label": "🚚 Regional Operator", "type": "persona", "channel": "Telegram", "color": "#B57A22"},
        {"id": "p_procurement", "label": "📋 Procurement Watcher", "type": "persona", "channel": "Email", "color": "#B57A22"},
        {"id": "p_resilience", "label": "⚡ Ops/Resilience", "type": "persona", "channel": "Telegram/SMS", "color": "#B94836"},
        {"id": "p_tourism", "label": "🏨 Tourism/Logistics", "type": "persona", "channel": "Telegram", "color": "#B6C74E"},
        {"id": "p_policy", "label": "📰 Policy/Media", "type": "persona", "channel": "Telegram Digest", "color": "#7F8C83"},
    ]

    # ── ARTIFACTS ──
    artifacts = [
        {"id": "art_desk", "label": "Dispatch Desk\n(dispatch_desk.md)", "type": "artifact", "description": "Decision clusters + persona routes", "color": "#18251F"},
        {"id": "art_dispatches", "label": "Opportunity\nDispatches", "type": "artifact", "description": "32 routed actions per cycle", "color": "#18251F"},
        {"id": "art_packs", "label": "Validation Packs\n(5 per cycle)", "type": "artifact", "description": "Sector hypotheses + procurement", "color": "#18251F"},
        {"id": "art_thesis", "label": "Regional Thesis\n+ Why Now", "type": "artifact", "description": "Cross-cluster synthesis", "color": "#18251F"},
        {"id": "art_backtest", "label": "Backtest Report\n(accuracy metrics)", "type": "artifact", "description": "Precision/recall per signal", "color": "#18251F"},
        {"id": "art_dashboard", "label": "Interactive\nDashboard", "type": "artifact", "description": "Map + theater + ask-the-desk", "color": "#18251F"},
        {"id": "art_community", "label": "Community Brief\n(WhatsApp/IG/X)", "type": "artifact", "description": "Plain-language signals", "color": "#18251F"},
        {"id": "art_api", "label": "HTTP API +\nMCP Adapter", "type": "artifact", "description": "Agent-agnostic interface", "color": "#18251F"},
    ]

    # Collect all nodes
    nodes.extend(sources)
    nodes.extend(watchers)
    nodes.append(merger)
    nodes.extend(signals)
    nodes.extend(personas)
    nodes.extend(artifacts)

    # ── EDGES: Source → Watcher ──
    source_watcher_map = {
        "src_wb": ["w_wb"],
        "src_idb": ["w_idb"],
        "src_caricom": ["w_tier2"],
        "src_cdb": ["w_tier2"],
        "src_ccrif": ["w_ccrif"],
        "src_eccb": ["w_eccb"],
        "src_noaa": ["w_noaa"],
        "src_ndbc": ["w_ndbc"],
        # NHC has implicit NOAA partnership
    }
    for src, watcher_list in source_watcher_map.items():
        for w in watcher_list:
            edges.append({"from": src, "to": w, "label": "fetches", "style": "solid"})

    # ── EDGES: Watcher → Merger ──
    for w in watchers:
        edges.append({"from": w["id"], "to": "merger", "label": "normalized JSON", "style": "solid"})

    # ── EDGES: Merger → Signals ──
    signal_sources = {
        "sig_cyclone": ["w_ndbc", "w_noaa"],
        "sig_maritime": ["w_ndbc", "w_noaa"],
        "sig_invest": ["w_wb", "w_idb"],
        "sig_enhanced": ["w_wb", "w_tier2"],
        "sig_vuln": ["w_wb"],
        "sig_tourism": ["w_wb", "w_noaa"],
        "sig_food": ["w_tier2", "w_wb"],
        "sig_dev": ["w_tier2", "w_idb"],
        "sig_supply": ["w_tier2", "w_ndbc"],
        "sig_ccrif": ["w_ccrif"],
        "sig_eccb_credit": ["w_eccb"],
        "sig_eccb_deposit": ["w_eccb"],
        "sig_trop_dev": ["w_nhc", "w_noaa"],
        "sig_active_storm": ["w_nhc"],
    }
    for sig, sources in signal_sources.items():
        for src in sources:
            edges.append({"from": src, "to": sig, "label": "composite rule", "style": "dashed"})

    # ── EDGES: Signals → Personas (routing rules) ──
    signal_persona_routes = {
        "sig_cyclone": ["p_resilience", "p_tourism"],
        "sig_maritime": ["p_resilience", "p_tourism"],
        "sig_invest": ["p_diaspora", "p_founder"],
        "sig_enhanced": ["p_diaspora", "p_ecosystem", "p_founder"],
        "sig_vuln": ["p_diaspora", "p_policy"],
        "sig_tourism": ["p_tourism", "p_founder"],
        "sig_food": ["p_ecosystem", "p_policy"],
        "sig_dev": ["p_regional", "p_procurement", "p_founder"],
        "sig_supply": ["p_regional", "p_procurement", "p_founder"],
        "sig_ccrif": ["p_diaspora", "p_policy", "p_resilience", "p_ecosystem"],
        "sig_eccb_credit": ["p_diaspora", "p_founder", "p_ecosystem", "p_regional"],
        "sig_eccb_deposit": ["p_diaspora", "p_ecosystem", "p_regional"],
        "sig_trop_dev": ["p_resilience"],
        "sig_active_storm": ["p_resilience"],
    }
    for sig, persona_list in signal_persona_routes.items():
        for p in persona_list:
            edges.append({"from": sig, "to": p, "label": "routed to", "style": "dotted"})

    # ── EDGES: Personas → Artifacts ──
    persona_artifact_routes = {
        "p_diaspora": ["art_desk", "art_dispatches", "art_packs", "art_backtest"],
        "p_founder": ["art_desk", "art_dispatches", "art_packs", "art_dashboard"],
        "p_ecosystem": ["art_desk", "art_packs", "art_thesis", "art_backtest"],
        "p_regional": ["art_desk", "art_dispatches", "art_packs"],
        "p_procurement": ["art_desk", "art_dispatches", "art_packs"],
        "p_resilience": ["art_desk", "art_dispatches", "art_community"],
        "p_tourism": ["art_desk", "art_dispatches", "art_dashboard"],
        "p_policy": ["art_desk", "art_thesis", "art_backtest", "art_community"],
    }
    for p, artifact_list in persona_artifact_routes.items():
        for a in artifact_list:
            edges.append({"from": p, "to": a, "label": "consumes", "style": "dotted"})

    # ── EDGES: Artifacts → API ──
    for a in artifacts:
        edges.append({"from": a["id"], "to": "art_api", "label": "served via", "style": "dashed"})

    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "title": "Abeng — Data Lineage & Routing Graph",
            "description": "8 sources → 8 watchers → merger → 14 signals → 11 personas → 8 artifacts → API",
            "version": "1.0",
            "cycle": "4-hour",
        },
    }


def main():
    graph = build_lineage_graph()

    # Export for graphify
    output = {
        "graph": graph,
        "config": {
            "layout": "hierarchical",
            "direction": "LR",
            "nodeSpacing": 100,
            "rankSpacing": 150,
            "edgeLabelFontSize": 10,
            "nodeLabelFontSize": 11,
        },
        "styles": {
            "source": {"shape": "box", "fillColor": "#E8F0FE", "borderColor": "#2676A8"},
            "watcher": {"shape": "ellipse", "fillColor": "#E8F0FE", "borderColor": "#2676A8"},
            "merger": {"shape": "diamond", "fillColor": "#F4EBDD", "borderColor": "#18251F"},
            "signal": {"shape": "hexagon", "fillColor": "#FEF3E2", "borderColor": "#B57A22"},
            "persona": {"shape": "circle", "fillColor": "#E6F2EC", "borderColor": "#0D766E"},
            "artifact": {"shape": "folder", "fillColor": "#F4EBDD", "borderColor": "#18251F"},
        },
    }

    GRAPH_OUT.parent.mkdir(parents=True, exist_ok=True)
    GRAPH_OUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Graph written to {GRAPH_OUT}")

    # Also generate a simple DOT file for Graphviz
    dot_path = GRAPH_OUT.with_suffix(".dot")
    generate_dot(graph, dot_path)
    print(f"✅ DOT file written to {dot_path}")


def generate_dot(graph: dict, path: Path):
    """Generate Graphviz DOT file for rendering."""
    lines = [
        "digraph Abeng {",
        '  rankdir=LR;',
        '  fontname="Inter";',
        '  fontsize=12;',
        '  nodesep=0.8;',
        '  ranksep=1.2;',
        '  splines=ortho;',
        '  compound=true;',
        "",
    ]

    # Node definitions with subgraphs for grouping
    subgraphs = {
        "Sources": [n for n in graph["nodes"] if n["type"] == "source"],
        "Watchers": [n for n in graph["nodes"] if n["type"] == "watcher"],
        "Merger": [n for n in graph["nodes"] if n["type"] == "merger"],
        "Signals": [n for n in graph["nodes"] if n["type"] == "signal"],
        "Personas": [n for n in graph["nodes"] if n["type"] == "persona"],
        "Artifacts": [n for n in graph["nodes"] if n["type"] == "artifact"],
    }

    for group_name, group_nodes in subgraphs.items():
        if not group_nodes:
            continue
        lines.append(f'  subgraph cluster_{group_name.lower()} {{')
        lines.append(f'    label="{group_name}";')
        lines.append('    style="rounded,filled";')
        lines.append('    fillcolor="#F8F8F8";')
        lines.append('    fontname="Inter Bold";')
        lines.append('    fontsize=13;')
        for n in group_nodes:
            shape_map = {
                "source": "box",
                "watcher": "ellipse",
                "merger": "diamond",
                "signal": "hexagon",
                "persona": "circle",
                "artifact": "folder",
            }
            shape = shape_map.get(n["type"], "box")
            color = n.get("color", "#18251F")
            label = n["label"].replace("\n", "\\n").replace('"', '\\"')
            lines.append(f'    {n["id"]} [shape={shape}, label="{label}", fillcolor="{color}", style="filled,rounded", fontname="Inter", fontsize=10];')
        lines.append("  }")
        lines.append("")

    # Edges
    for e in graph["edges"]:
        style_map = {"solid": "solid", "dashed": "dashed", "dotted": "dotted"}
        style = style_map.get(e.get("style", "solid"), "solid")
        label = e.get("label", "").replace('"', '\\"')
        lines.append(f'  {e["from"]} -> {e["to"]} [label="{label}", style={style}, fontname="Inter", fontsize=8, color="#7F8C83", penwidth=1.2];')

    lines.append("}")
    dot_content = "\n".join(lines)

    path = Path.cwd() / "dashboard" / "abeng-lineage.dot"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()