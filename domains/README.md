# Domains — the engine's instances

Abeng is **domain-agnostic**. The same pipeline —
**watch → reason → distribute** — runs every instance. A *domain* is a
declarative manifest in this folder that says, for one instance:

- **which public sources** it watches (and the watcher + config that wire them)
- **which signal rules** it reasons over
- **which recipients** it distributes to, and on what channel

Standing up a new instance is **a config file, not a rebuild.**

## The contract

Every `domains/*.json` manifest has this shape (validated by `registry.py`):

```jsonc
{
  "id": "caribbean",                 // unique slug
  "name": "Caribbean Economic Signals",
  "status": "live",                  // "live" | "blueprint"
  "tagline": "…", "blurb": "…",
  "pipeline": {                      // the three engine stages, in plain language
    "watch": "…", "reason": "…", "distribute": "…"
  },
  "sources": [                       // each source = a watcher + its config
    { "id": "world_bank", "label": "World Bank Indicators",
      "kind": "economic",
      "watcher": "watchers/world_bank_poller.py",   // null = not yet wired
      "config":  "config/world_bank_indicators.json" }
  ],
  "signals":    { "config": "config/composite_rules.json", "kinds": [ … ] },
  "recipients": { "config": "config/recipients.json", "personas": [ … ] }
}
```

`status`:
- **`live`** — every source has a real `watcher`; the instance runs in the pipeline today.
- **`blueprint`** — defined on the identical engine; some sources not yet wired
  (`"watcher": null`). Proves the engine generalises without claiming live data.

## Registry

`registry.py` loads, validates, and lists all manifests:

```bash
python3 domains/registry.py            # human table
python3 domains/registry.py --json     # machine-readable (served at /api/domains)
python3 domains/registry.py --validate # exit 1 on any error  (CI-friendly)
```

The configurator UI's domain switcher renders straight from `/api/domains`,
so **dropping a new manifest in this folder makes a new domain appear** —
the abstraction is enforced in code, not just described in copy.

## Current domains

| id | status | what it shows |
|----|--------|----------------|
| `caribbean` | **live** | the working instance — 6 sources, 9 signal rules, 8 recipient roles |
| `climate` | blueprint | re-targets the already-wired NOAA/NDBC/NHC watchers at insurers & resilience planners |
| `trade` | blueprint | reuses CARICOM trade feeds; adds port/shipping sources |
| `capital` | blueprint | same World Bank watcher, broader emerging-market country set |
| `compliance` | blueprint | regulatory gazettes & sanctions → obligation mapping |

To add one: copy a manifest, change `id`/`name`/sources/signals/recipients,
set `status` honestly, and run `registry.py --validate`.
