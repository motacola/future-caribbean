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
            "name": "status",
            "description": "Get the current engine status: source health, cycle info, dispatch counts, feedback outcomes, pipeline state.",
            "method": "GET",
            "path": "/api/status",
            "params": {"type": "object", "properties": {}},
            "example_request": {},
            "example_response_keys": ["ok", "sources", "n_sources_ok", "n_dispatches", "n_clusters", "cycle_id", "generated_at", "cadence_hours", "cycle_count", "feedback", "pipeline_running"]
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
        }
    ]
}
