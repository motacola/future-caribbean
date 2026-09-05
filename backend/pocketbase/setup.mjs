#!/usr/bin/env node
/**
 * Abeng → PocketBase schema bootstrap.
 *
 * Run against a LIVE PocketBase instance:
 *   PB_URL=https://pb.yourhost.com PB_ADMIN_EMAIL=you@x.com PB_ADMIN_PASSWORD=... node setup.mjs
 *
 * What this creates (mapped 1:1 from the current JSON-file state layer):
 *   users        (auth)   operator/editor desk accounts + role
 *   sources               config/*_sources.json  → wired/configured/live/stale
 *   observations          data/<source>/latest.json (dedup by fingerprint)
 *   signals               composite signals (map + leaderboard data)
 *   rules                 config/composite_rules.json
 *   recipients            config/recipients.json (personas)
 *   interventions         track_record.json rows (state machine + scores)
 *   suppliers             verified-capability leaderboard
 *   outcomes              submit_outcome events (supplier_validated +4 / intro_accepted +3 / blocked_logistics)
 *   campaigns             operator campaigns
 *   packs                 outbox/*.json (briefs, validation packs)
 *   assets                file storage for pack attachments / generated PDFs / map images
 *
 * Design rules:
 *   - Public (anonymous Vercel frontend) gets READ on live sources, signals, verified
 *     interventions, packs, recipients, rules. viewRule:"" = public; filtered rules enforce scope.
 *   - Operators (role=operator|admin) get CREATE/UPDATE on interventions/outcomes/suppliers/campaigns.
 *   - The 4h pipeline bot authenticates as ADMIN (X-Admin-Auth-Token) and upserts
 *     sources/observations/signals/packs/rules — admin bypasses collection rules.
 *   - Many-to-many source lists on signals are stored as a JSON array of source names
 *     (denormalized) to avoid multi-relation fragility; relation fields are single (maxSelect:1).
 */

import PocketBase from "pocketbase";

const PB_URL = process.env.PB_URL || "http://127.0.0.1:8090";
const ADMIN_EMAIL = process.env.PB_ADMIN_EMAIL;
const ADMIN_PASSWORD = process.env.PB_ADMIN_PASSWORD;

if (!ADMIN_EMAIL || !ADMIN_PASSWORD) {
  console.error("Set PB_ADMIN_EMAIL and PB_ADMIN_PASSWORD (or PB_ADMIN_TOKEN).");
  process.exit(1);
}

const pb = new PocketBase(PB_URL);
await pb.admins.authWithPassword(ADMIN_EMAIL, ADMIN_PASSWORD);

// --- helpers -------------------------------------------------------------
const txt = (name, opt = {}) => ({ name, type: "text", required: false, ...opt });
const num = (name, opt = {}) => ({ name, type: "number", required: false, ...opt });
const bool = (name, opt = {}) => ({ name, type: "bool", required: false, ...opt });
const date = (name, opt = {}) => ({ name, type: "date", required: false, ...opt });
const json = (name, opt = {}) => ({ name, type: "json", required: false, ...opt });
const sel = (name, values, opt = {}) => ({
  name, type: "select", required: false, values, maxSelect: 1, ...opt,
});
const rel = (name, collection, opt = {}) => ({
  name, type: "relation", required: false, collectionId: collection,
  maxSelect: 1, cascadeDelete: false, ...opt,
});
const url = (name, opt = {}) => ({ name, type: "url", required: false, ...opt });
const file = (name, opt = {}) => ({
  name, type: "file", required: false, maxSelect: 1,
  mimeTypes: ["application/json", "application/pdf", "image/png", "image/jpeg", "image/svg+xml"], ...opt,
});

// Rule strings
const PUBLIC = "";                                  // anyone can read
const OPERATOR_WRITE = "@request.auth.role = 'operator' || @request.auth.role = 'admin'";
const ADMIN_ONLY = "@request.auth.role = 'admin'";
async function make(collection) {
  // Use collections.import() for idempotent upsert by name (no delete/create race,
  // and works even when an auth collection already exists).
  try {
    await pb.collections.import([collection], false);
    const created = await pb.collections.getList(1, 1, { filter: `name = "${collection.name}"` });
    console.log(`  + upserted ${collection.name} (${created.items[0]?.id})`);
    return created.items[0];
  } catch (e) {
    console.error(`  ✗ FAILED ${collection.name}:`, JSON.stringify(e?.response?.data || e.message));
    throw e;
  }
}

// --- 1. users (auth) -----------------------------------------------------
const users = await make({
  name: "users",
  type: "auth",
  fields: [
    txt("displayName"),
    sel("role", ["admin", "operator", "viewer"]),
  ],
  listRule: ADMIN_ONLY,
  viewRule: "@request.auth.id = @collection.users.id || @request.auth.role = 'admin'",
  createRule: ADMIN_ONLY,
  updateRule: "@request.auth.id = @collection.users.id || @request.auth.role = 'admin'",
  deleteRule: ADMIN_ONLY,
});

// --- 2. sources ----------------------------------------------------------
const sources = await make({
  name: "sources",
  type: "base",
  fields: [
    txt("name", { required: true }),
    sel("kind", ["worldbank", "idb", "noaa", "ndbc", "caricom", "cdb", "tenders", "nhc", "other"]),
    txt("region", { value: "Caribbean" }),
    sel("status", ["wired", "configured", "live", "stale"]),
    url("homepage"),
    date("lastFetched"),
  ],
  listRule: "status = 'live' || @request.auth.role = 'operator' || @request.auth.role = 'admin'",
  viewRule: "status = 'live' || @request.auth.role = 'operator' || @request.auth.role = 'admin'",
  createRule: ADMIN_ONLY,
  updateRule: ADMIN_ONLY,
  deleteRule: ADMIN_ONLY,
});

// --- 3. observations -----------------------------------------------------
const observations = await make({
  name: "observations",
  type: "base",
  fields: [
    rel("source", sources.id),
    txt("fingerprint", { required: true }),
    txt("period"),
    num("value"),
    json("payload"),
  ],
  listRule: "source.status = 'live' || @request.auth.role = 'operator' || @request.auth.role = 'admin'",
  viewRule: "source.status = 'live' || @request.auth.role = 'operator' || @request.auth.role = 'admin'",
  createRule: ADMIN_ONLY,
  updateRule: ADMIN_ONLY,
  deleteRule: ADMIN_ONLY,
});

// --- 4. signals (map + leaderboard) -------------------------------------
const signals = await make({
  name: "signals",
  type: "base",
  fields: [
    txt("kind", { required: true }),        // e.g. climate_risk, msme_credit, villa_copilot
    txt("label"),
    sel("priority", ["low", "medium", "high", "critical"]),
    txt("country"),                          // Caribbean-only
    num("score"),
    num("evidenceCount"),
    json("sourceRefs"),                      // denormalized [{name, kind}]
    json("raw"),
  ],
  listRule: PUBLIC,
  viewRule: PUBLIC,
  createRule: ADMIN_ONLY,
  updateRule: ADMIN_ONLY,
  deleteRule: ADMIN_ONLY,
});

// --- 5. rules (composite_rules.json) ------------------------------------
const rules = await make({
  name: "rules",
  type: "base",
  fields: [
    txt("kind", { required: true }),
    txt("label"),
    sel("priority", ["low", "medium", "high", "critical"]),
    json("conditions"),
  ],
  listRule: PUBLIC,
  viewRule: PUBLIC,
  createRule: ADMIN_ONLY,
  updateRule: ADMIN_ONLY,
  deleteRule: ADMIN_ONLY,
});

// --- 6. recipients (personas / recipients.json) -------------------------
const recipients = await make({
  name: "recipients",
  type: "base",
  fields: [
    txt("key", { required: true }),
    txt("label"),
    txt("actionWindow"),
    txt("decisionToInfluence"),
    json("routingRationale"),
  ],
  listRule: PUBLIC,
  viewRule: PUBLIC,
  createRule: ADMIN_ONLY,
  updateRule: ADMIN_ONLY,
  deleteRule: ADMIN_ONLY,
});

// --- 7. campaigns --------------------------------------------------------
const campaigns = await make({
  name: "campaigns",
  type: "base",
  fields: [
    txt("slug"),
    num("interventionCount"),
    num("activeCount"),
    txt("ownerPersona"),
    txt("blocker"),
    txt("interventionType"),
    json("interventionIds"),
    date("updatedAt"),
  ],
  listRule: PUBLIC,
  viewRule: PUBLIC,
  createRule: OPERATOR_WRITE,
  updateRule: OPERATOR_WRITE,
  deleteRule: ADMIN_ONLY,
});

// --- 8. suppliers (verified-capability leaderboard) --------------------
const suppliers = await make({
  name: "suppliers",
  type: "base",
  fields: [
    txt("name", { required: true }),
    txt("country"),
    num("validatedCount"),
    num("score"),
  ],
  listRule: PUBLIC,
  viewRule: PUBLIC,
  createRule: OPERATOR_WRITE,
  updateRule: OPERATOR_WRITE,
  deleteRule: ADMIN_ONLY,
});

// --- 9. interventions (data/coordination/intervention_state.json) ------
// Real fields from coordination/interventions.py:
//   id (string), status (lifecycle), owner_persona, blocker,
//   evidence[] ({summary,source,country?}), related_signals[],
//   verified_edge {country,capability}, verified_at, created_at, updated_at
const interventions = await make({
  name: "interventions",
  type: "base",
  fields: [
    txt("stateId", { required: true }),     // the long intervention id (unique key)
    txt("country"),
    txt("blocker"),
    txt("ownerPersona"),
    sel("status", ["proposed", "evidence_requested", "evidence_received", "verified", "rejected", "expired"]),
    json("evidence"),                        // array of cited evidence records
    json("relatedSignals"),                  // array of signal ids
    json("verifiedEdge"),                    // {country, capability} once verified
    json("scoreChanges"),                    // before/after score deltas from verify()
    date("createdAt"),
    date("verifiedAt"),
    date("updatedAt"),
  ],
  listRule: "status = 'verified' || @request.auth.role = 'operator' || @request.auth.role = 'admin'",
  viewRule: "status = 'verified' || @request.auth.role = 'operator' || @request.auth.role = 'admin'",
  createRule: OPERATOR_WRITE,
  updateRule: OPERATOR_WRITE,
  deleteRule: ADMIN_ONLY,
});

// --- 10. outcomes (flattened from each intervention's nested outcomes[]) -
// Real OUTCOME_TYPES: supplier_validated (+4), intro_accepted (+3), blocked_logistics (0)
const outcomes = await make({
  name: "outcomes",
  type: "base",
  fields: [
    rel("intervention", interventions.id),
    sel("type", ["supplier_validated", "intro_accepted", "blocked_logistics", "other"]),
    num("delta"),                            // +4 / +3 / 0
    txt("note"),
    date("submittedAt"),
  ],
  listRule: "intervention.status = 'verified' || @request.auth.role = 'operator' || @request.auth.role = 'admin'",
  viewRule: "intervention.status = 'verified' || @request.auth.role = 'operator' || @request.auth.role = 'admin'",
  createRule: OPERATOR_WRITE,
  updateRule: OPERATOR_WRITE,
  deleteRule: ADMIN_ONLY,
});

// --- 11. packs (outbox/*.json) ------------------------------------------
const packs = await make({
  name: "packs",
  type: "base",
  fields: [
    sel("kind", ["dispatch_desk", "opportunity_dispatch", "validation_pack", "telegram_brief", "community_brief"]),
    rel("signal", signals.id),
    json("body"),
    txt("fileName"),
    file("attachment"),
  ],
  listRule: PUBLIC,
  viewRule: PUBLIC,
  createRule: ADMIN_ONLY,
  updateRule: ADMIN_ONLY,
  deleteRule: ADMIN_ONLY,
});

console.log("Abeng PocketBase schema created:");
for (const c of [users, sources, observations, signals, rules, recipients, campaigns, suppliers, interventions, outcomes, packs]) {
  console.log(`  - ${c.name} (${c.id})`);
}
console.log("\nNext: configure CORS to allow https://abeng.vercel.app, then run sync_to_pb.mjs in the pipeline.");
