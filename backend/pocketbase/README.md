# Signal Fabric × PocketBase — Backend Design

**Problem PocketBase solves here.** Signal Fabric's state currently lives in three places that don't compose:
1. **JSON files in git** (`track_record.json`, `recipients.json`, `composite_rules.json`, `data/*.json`, `outbox/*.json`) — committed by the 4h GitHub Action. Up to 4h stale on the public site; no auth; no concurrent writes.
2. **`server.py`** (`@vercel/python` serverless) — serves those JSON files over HTTP; public writes are disabled (`writes: False`).
3. **`coordination/console.py`** — a local web operator console for `verify()` / `submit_outcome`.

PocketBase replaces #1's role as the system of record and #3's role as the operator desk, and gives you three things the JSON model can't: **realtime**, **auth/roles**, and **multi-user operator writes** — while keeping the Python pipeline and the Vercel frontend.

## Topology change (the one real decision)

PocketBase is a long-lived Go binary + SQLite. **Vercel cannot host it.** So you add one persistent backend:

```
GitHub Actions (4h) ──admin token──▶ PocketBase  ──realtime/REST──▶ Vercel Astro frontend
        │  (watchers→mergers→packagers)            ▲                        │
        └──────────── commits JSON as fallback ───┘   operator console ────┘
```

Host PB on a self-hosted server (small VPS / your always-on node) with TLS in front. The Vercel frontend becomes a *reader + realtime subscriber*; the 4h pipeline becomes a *writer*; the operator desk becomes *authenticated writes*.

## Collections (see `setup.mjs` for the runnable schema)

| Collection | Replaces | Public read? | Writes |
|---|---|---|---|
| `users` (auth) | operator console accounts | no | admin |
| `sources` | `config/*_sources.json` | live only | pipeline (admin) |
| `observations` | `data/<source>/latest.json` | live only | pipeline (admin) |
| `signals` | composite signals | ✅ | pipeline (admin) |
| `rules` | `composite_rules.json` | ✅ | pipeline (admin) |
| `recipients` | `recipients.json` | ✅ | pipeline (admin) |
| `campaigns` | — | ✅ | operator |
| `suppliers` | verified-capability leaderboard | ✅ | operator |
| `interventions` | `track_record.json` | verified only | operator |
| `outcomes` | `submit_outcome` events | verified only | operator |
| `packs` | `outbox/*.json` | ✅ | pipeline (admin) |

## Auth roles

- **admin** — the 4h pipeline bot (authenticated via `X-Admin-Auth-Token`); full write, bypasses collection rules.
- **operator** — humans running `verify()` / `submit_outcome` from the desk. `createRule`/`updateRule` = `@request.auth.role = 'operator' || 'admin'`.
- **viewer / anonymous** — the Vercel frontend. Read-only, scoped by `viewRule` (e.g. interventions only when `status = 'verified'`).

## Realtime leaderboard (the payoff)

The homepage map + "My Signal Desk" currently re-render from committed JSON (≤4h lag). With PB:

```ts
// Astro client component (see realtime-leaderboard.example.ts)
const unsub = await pb.collection("signals").subscribe("*", (e) => {
  if (e.action === "update" || e.action === "create") updateMapMarker(e.record);
});
// desk live updates on verification:
await pb.collection("interventions").subscribe("verified", (e) => updateDesk(e.record));
```

When an operator verifies an intervention (`status → verified`, `afterScore` set, `capabilityEdges` cited), **every open browser updates instantly** — no redeploy, no 4h wait. This is the single biggest UX win and the reason PB beats "keep committing JSON."

## Vercel frontend integration — verdict: ✅ clean

1. **Add the SDK:** `npm i @pocketbase/js` to the Astro/frontend project. PB ships a first-class JS SDK (browser + Node).
2. **SSR pages** (`regional-connections.astro`, `/build` desk): fetch server-side at request time via `pb.collection(...).getList()` → always fresh, kills the 4h staleness without touching page logic beyond the data source.
3. **Client realtime:** init `new PocketBase(PB_URL)` in an island, `subscribe()` on mount, `unsubscribe()` on destroy.
4. **CORS:** PB Settings → add `https://signal-fabric.vercel.app` (and your preview `*.vercel.app`). Without this the browser calls are blocked.
5. **Operator auth:** login form → `pb.collection('users').authWithPassword` → `authStore` token sent on `verify()`/`submit_outcome` calls.
6. **Agent contract:** keep `api_manifest.py` + `server.py` as the Hermes/MCP tool surface, but back reads with PB (or point agents straight at PB REST). Writes stay operator-authed.

No rewrite of the Astro routes is needed — only the data-fetch layer swaps from "read committed JSON" to "read PB collection." Realtime is additive.

## Migration path (low-risk, reversible)

- **Phase 0** — Stand up PB; run `setup.mjs`. Configure CORS.
- **Phase 1** — Add `sync_to_pb.mjs` as a step in `run_pipeline.sh` that upserts `sources/observations/signals/packs/rules/recipients` after generation. **Keep JSON commits as fallback** so the site still works if PB is down.
- **Phase 2** — Frontend reads from PB (SSR + client). Flip homepage map + desk to realtime subscriptions.
- **Phase 3** — Port `coordination/console.py` to PB auth + `interventions`/`outcomes` collections. Retire `track_record.json` writes.
- **Phase 4** — Retire `server.py` JSON endpoints (or keep as a thin PB proxy for agents).

## Tradeoffs (stated honestly)

- **You now run a server:** TLS, SQLite backup (the 4h Action can also `pb` export), and PB version updates. More ops than static Vercel.
- **Pre-1.0:** PB is v0.39.6 — API is stable in practice but not version-guaranteed. Pin the version.
- **Latency hop:** a US-East PB talking to Caribbean users is fine for a dashboard; host closer (Fly `mia`/`gru`) if needed.
- **Gain:** realtime, auth, multi-operator desk, no 4h staleness, structured queries/filters instead of JSON grep.

## Verification (run against live PocketBase 0.39.6)

All 11 collections bootstrap idempotently via `setup.mjs` (`collections.import`, not delete/create).
Security model confirmed against the **real public REST path** (`GET /api/collections/<c>/records`):

- ✅ Anonymous READ of `verified` interventions / `live` sources → allowed (public leaderboard)
- ✅ Anonymous READ of `proposed`/non-verified records → **blocked** (no leak)
- ✅ Anonymous WRITE → blocked (HTTP 400)
- ✅ Operator can propose → verify → record becomes public instantly
- ✅ Operator sees proposed records (can work the desk); anonymous cannot

**Critical pitfall (caught during verification):** PocketBase list endpoints enforce `listRule`,
NOT `viewRule`. `viewRule` only guards single-record GET-by-ID. A `listRule: ""` (public)
leaks every record via the list endpoint regardless of `viewRule`. For `interventions`,
`outcomes`, `sources`, `observations` the `listRule` must itself restrict to the public subset
(`status = 'verified'`, `status = 'live'`) while still letting `operator`/`admin` see all.
This is encoded in `setup.mjs`.

**Realtime note:** the frontend realtime layer (`src/scripts/desk-realtime.ts`) uses the
browser `EventSource` API via the PocketBase JS SDK. It is **additive** — it only seeds +
patches a dedicated `#pb-live-feed` container; it never mutates the build-time-rendered cards.
If `PUBLIC_PB_URL` is unset, the SDK is tree-shaken out of the client bundle entirely (zero
bytes, zero runtime cost) and the page is byte-for-byte the committed-JSON build.

**Verified live (browser + real PB):** with `PUBLIC_PB_URL` set, the feed seeds verified
interventions from PB on load, and when an operator verifies an intervention via the API,
the browser feed updates from 1 → 2 items **without a page reload** (SSE push). No regression
to the static page when PB is down.

**SDK vendoring (important):** Astro/Vite externalizes the `pocketbase` npm package for client
scripts (tree-shakes it to nothing). The SDK is vendored at `src/lib/vendor/pocketbase.mjs`
(pinned ESM build) and imported locally so it bundles into the client. `package.json` keeps
`pocketbase` as a devDependency for version tracking, but the shipped code uses the vendored copy.
To upgrade: copy `node_modules/pocketbase/dist/pocketbase.es.mjs` → `src/lib/vendor/pocketbase.mjs`.

**Local-dev gotchas (so you don't lose an hour):**
- `pocketbase superuser` CLI defaults `--dir` to its own default, NOT the `--dir` your `serve`
  used. Always pass `--dir` explicitly to both, or auth silently hits a different DB.
- Stale `pb_migrations/*.js` from a partial run will block every fresh `serve` with
  "collectionId doesn't exist". Nuke the migrations dir + data dir together before retrying.
- The npm `pocketbase` SDK version (e.g. `0.27.0`) is independent of the server binary version
  (`0.39.6`); the REST API is stable across them. Pin the SDK, don't match the binary number.

## Run it

```bash
# one-time: create superuser in the SAME --dir your server uses
pocketbase superuser create you@x.com StrongPass123! --dir=/path/to/pb_data

PB_URL=https://pb.yourhost.com PB_ADMIN_EMAIL=you@x.com PB_ADMIN_PASSWORD=... \
  node setup.mjs
```

Then point the Vercel frontend at `PB_URL`, add `https://signal-fabric.vercel.app` to
PocketBase Settings → CORS, and switch the Astro data layer from "read committed JSON" to
"read PB collection" using the SDK + `realtime-leaderboard.example.ts`.
