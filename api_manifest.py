"""Shared tool manifest — imported by server.py (local) and api/tools.py (Vercel)."""

TOOLS_MANIFEST = {
    "engine": "Signal Fabric",
    "product": "Signal Fabric",
    "version": 1,
    "tools": [
        {
            "name": "live_feed",
            "description": "RSS 2.0 feed of the latest signals in plain language (one item per signal, machine ids in guid/category)",
            "method": "GET",
            "path": "/feed.xml",
            "params": {},
            "writes": False,
        },
        {
            "name": "ask",
            "description": "Ask a deterministic question against the current Dispatch Desk. Returns a cited answer from live data — no LLM generation.",
            "method": "POST",
            "path": "/api/ask",
            "params": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Natural-language question about today's signals, countries, personas, feedback changes, or drafting notes."}
                },
                "required": ["question"]
            },
            "example_request": {"question": "explain the lead signal"},
            "example_response_keys": ["question", "answer", "engine", "generated_at"]
        },
        {
            "name": "regional_news.list",
            "description": "Ranked Caribbean news with deterministic source-tier, freshness, country, topic, and finance-relevance metadata.",
            "method": "GET",
            "path": "/api/regional-news",
            "params": {"type": "object", "properties": {"country": {"type": "string"}, "topic": {"type": "string"}, "limit": {"type": "integer"}}},
            "example_request": {"country": "Barbados", "topic": "finance"},
            "example_response_keys": ["ok", "fetched_at", "count", "items"],
            "writes": False
        },
        {
            "name": "status",
            "description": "Get the current engine status: source health, cycle info, dispatch counts, feedback outcomes, pipeline state.",
            "method": "GET",
            "path": "/api/status",
            "params": {"type": "object", "properties": {}},
            "example_request": {},
            "example_response_keys": ["ok", "sources", "n_sources_ok", "n_dispatches", "n_clusters", "cycle_id", "generated_at", "cadence_hours", "cycle_count", "feedback", "pipeline_running"]
        },
        {
            "name": "accuracy",
            "description": "Get the desk's public accuracy record: Brier score vs naive baseline, externally-resolved-only Brier, public commitment milestones, resolution mix by confidence band, and ledger chain integrity.",
            "method": "GET",
            "path": "/api/calibration",
            "params": {"type": "object", "properties": {}},
            "example_request": {},
            "example_response_keys": ["ok", "committed_at", "days_elapsed", "commitments", "brier", "brier_naive_baseline", "brier_improvement_over_naive", "brier_external_only", "external_resolved_n", "externally_resolved", "bands", "chain_intact"]
        },
        {
            "name": "validation_packs.index",
            "description": "List all validation packs for the current cycle with signal_id, country, recommendation, and confidence.",
            "method": "GET",
            "path": "/api/validation-packs",
            "params": {"type": "object", "properties": {}},
            "example_request": {},
            "example_response_keys": ["generated_at", "packs"]
        },
        {
            "name": "validation_packs.get",
            "description": "Get a full validation pack by signal_id. Contains sector hypotheses, supporting projects, procurement matches, intro targets, and unresolved questions.",
            "method": "GET",
            "path": "/api/validation-packs/{signal_id}",
            "params": {
                "type": "object",
                "properties": {
                    "signal_id": {"type": "string", "description": "The signal identifier (e.g., enhanced-invest-guyana)"}
                },
                "required": ["signal_id"]
            },
            "example_request": {"signal_id": "enhanced-invest-guyana"},
            "bundle": "GET /api/validation-packs/bundle returns every current pack (.json + .md) as one zip download",
            "example_response_keys": ["signal_id", "country", "sector_hypotheses", "supporting_projects", "procurement_matches", "advance_or_reject_recommendation", "recommendation_reason", "last_validated_at"]
        },
        {
            "name": "domains",
            "description": "List all configured engine instances (domains) — live and blueprint — with source/signal/recipient counts.",
            "method": "GET",
            "path": "/api/domains",
            "params": {"type": "object", "properties": {}},
            "example_request": {},
            "example_response_keys": ["ok", "count", "domains", "errors"]
        },
        {
            "name": "reasoning",
            "description": "Get the reasoning agent's cross-signal synthesis for the current cycle.",
            "method": "GET",
            "path": "/api/reasoning",
            "params": {"type": "object", "properties": {}},
            "example_request": {},
            "example_response_keys": ["ok", "engine", "model", "thesis", "connections"]
        },
        {
            "name": "procurement_outcomes.list",
            "description": "Canonical Caribbean tender records with detection date, closing-date amendments, and recorded outcome (awarded/cancelled/unresolved). Supplier and award value appear only where a source states them; `resolution.independence` reports how much distance the resolving source has from the source that generated the claim.",
            "method": "GET",
            "path": "/api/procurement-outcomes",
            "params": {
                "type": "object",
                "properties": {
                    "country": {"type": "string", "description": "Filter to one jurisdiction, e.g. Guyana"},
                    "state": {"type": "string", "description": "detected|open|amended|closed|awarded|cancelled|unresolved"},
                    "resolved": {"type": "boolean", "description": "Only tenders with a recorded outcome"},
                    "limit": {"type": "integer", "description": "Max records returned (default 100, max 500)"}
                }
            },
            "example_request": {"country": "Guyana", "state": "closed", "limit": 10},
            "example_response_keys": ["ok", "summary", "provenance", "count", "tenders"],
            "writes": False
        },
        {
            "name": "track_record",
            "description": "Public record of what the desk said each cycle, feedback provenance, responses, and current priority adjustments",
            "method": "GET",
            "path": "/api/track-record",
            "params": {"type": "object", "properties": {}},
            "example_request": {},
            "example_response_keys": ["ok", "generated_at", "feedback_provenance", "current_boosts", "cycles"],
            "writes": False
        },
        {
            "name": "feedback_apply",
            "description": "Apply recipient feedback to adjust signal priorities for the next cycle. This is a write operation.",
            "method": "POST",
            "path": "/api/feedback/apply",
            "params": {
                "type": "object",
                "properties": {}
            },
            "example_request": {},
            "example_response_keys": ["ok", "workflow", "exit_code", "result"],
            "writes": True
        },
        {
            "name": "community_brief.get",
            "description": "Get the plain-language community brief — one paragraph per signal, no jargon, for builders and community leaders.",
            "method": "GET",
            "path": "/api/community-brief",
            "params": {"type": "object", "properties": {}},
            "example_request": {},
            "example_response_keys": ["ok", "brief"],
            "writes": False
        },
        {
            "name": "community_brief.snippets",
            "description": "Get platform-specific social snippets (X thread, Instagram caption, WhatsApp forward) for the current community brief.",
            "method": "GET",
            "path": "/api/community-brief/snippets",
            "params": {"type": "object", "properties": {}},
            "example_request": {},
            "example_response_keys": ["ok", "snippets"],
            "writes": False
        },
        {
            "name": "coordination_opportunities.index",
            "description": "List deterministic cross-island coordination candidates, matched capabilities, frictions, evidence, and explainable score components.",
            "method": "GET",
            "path": "/api/coordination-opportunities",
            "params": {"type": "object", "properties": {}},
            "example_request": {},
            "example_response_keys": ["engine", "registry_status", "count", "opportunities"],
            "writes": False
        },
        {
            "name": "coordination_opportunities.get",
            "description": "Get one coordination candidate by stable id, including project demand, contributing nodes, missing capabilities, frictions, owned unlock interventions, score-uplift estimates, and cited evidence.",
            "method": "GET",
            "path": "/api/coordination-opportunities/{opportunity_id}",
            "params": {
                "type": "object",
                "properties": {"opportunity_id": {"type": "string"}},
                "required": ["opportunity_id"]
            },
            "example_request": {"opportunity_id": "coord-dev-pipeline-regional"},
            "example_response_keys": ["id", "demand_node", "project_coordination_matches", "contributing_nodes", "frictions", "unlock_path", "minimum_next_action", "coordination_score"],
            "writes": False
        },
        {
            "name": "capability_matches.list",
            "description": "Detected Caribbean tenders matched to cited country/bloc capability-registry entries. Each match classifies the tender's required capability with deterministic keyword rules and carries the registry source, URL, and grade. This is screening evidence, not audited supplier capacity; unmatched capabilities are never guessed.",
            "method": "GET",
            "path": "/api/capability-matches",
            "params": {
                "type": "object",
                "properties": {
                    "country": {"type": "string", "description": "Filter matches to tenders from one jurisdiction, e.g. Guyana"},
                    "capability": {"type": "string", "description": "Filter to matches requiring a capability id, e.g. water_infrastructure"},
                    "limit": {"type": "integer", "description": "Max matches returned (default 100, max 500)"}
                }
            },
            "example_request": {"capability": "water_infrastructure", "limit": 10},
            "example_response_keys": ["ok", "registry_status", "classified_tenders", "tenders_with_capability_match", "by_capability", "by_country", "count_semantics", "count", "matches"],
            "writes": False
        }
    ]
}
