#!/usr/bin/env node
/**
 * sync_to_pb.mjs — Abeng → PocketBase pipeline sync step.
 *
 * Run AFTER the pipeline generates artifacts (as a step in run_pipeline.sh, or standalone):
 *   node sync_to_pb.mjs
 *
 * Reads the real Abeng state files and upserts them into PocketBase:
 *   data/coordination/intervention_state.json  → interventions + campaigns (+ flattened outcomes)
 *   data/sources/*.json (watcher latest)        → sources / observations (optional, if present)
 *   outbox/*.json (packs)                        → packs (optional, if present)
 *
 * Design:
 *   - Authenticates as ADMIN (X-Admin-Auth-Token) so it bypasses collection rules.
 *   - Idempotent upsert: interventions keyed by `stateId`; outcomes keyed by (intervention+type+submittedAt).
 *   - Never deletes records (so operator edits in PB are preserved across pipeline runs).
 *   - The committed JSON remains the fallback; this is ADDITIVE, not a replacement.
 *   - Safe to run even if PB is down: prints a clear warning and exits 0 (pipeline continues).
 *
 * Env:
 *   PB_URL            (default http://127.0.0.1:8090)
 *   PB_ADMIN_EMAIL / PB_ADMIN_PASSWORD   OR   PB_ADMIN_TOKEN
 *   SF_ROOT           (default: parent of this file's ../.. i.e. the future-caribbean repo root)
 */

import PocketBase from "pocketbase";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SF_ROOT = process.env.SF_ROOT || resolve(__dirname, "../../../clawd/projects/future-caribbean");
const PB_URL = process.env.PB_URL || "http://127.0.0.1:8090";

const pb = new PocketBase(PB_URL);

// ---- auth --------------------------------------------------------------
async function auth() {
  if (process.env.PB_ADMIN_TOKEN) {
    pb.authStore.save(process.env.PB_ADMIN_TOKEN);
    return;
  }
  const email = process.env.PB_ADMIN_EMAIL;
  const pass = process.env.PB_ADMIN_PASSWORD;
  if (!email || !pass) {
    throw new Error("Set PB_ADMIN_EMAIL/PB_ADMIN_PASSWORD or PB_ADMIN_TOKEN");
  }
  await pb.admins.authWithPassword(email, pass);
}

// ---- helpers -----------------------------------------------------------
function readJson(path) {
  if (!existsSync(path)) return null;
  try { return JSON.parse(readFileSync(path, "utf-8")); }
  catch (e) { console.warn(`  ⚠ could not parse ${path}: ${e.message}`); return null; }
}
function toDate(s) { return s ? new Date(s).toISOString() : null; }

// stable short hash for records that lack a natural id (signals in watcher JSON)
function shortHash(s) {
  const str = typeof s === "string" ? s : JSON.stringify(s);
  let h = 5381;
  for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) >>> 0;
  return h.toString(36);
}

// upsert helper: find by filter, create or update
async function upsert(collection, filter, data) {
  try {
    const list = await pb.collection(collection).getList(1, 1, { filter });
    if (list.items.length > 0) {
      return await pb.collection(collection).update(list.items[0].id, data);
    }
    return await pb.collection(collection).create(data);
  } catch (e) {
    const detail = e?.response?.data ? JSON.stringify(e.response.data) : e.message;
    console.warn(`  ⚠ upsert ${collection} failed: ${detail}`);
    return null;
  }
}

const OUTCOME_DELTA = { supplier_validated: 4, intro_accepted: 3, blocked_logistics: 0 };

// ---- main --------------------------------------------------------------
let synced = { interventions: 0, campaigns: 0, outcomes: 0, sources: 0, observations: 0, packs: 0 };

async function syncInterventions() {
  const path = resolve(SF_ROOT, "data/coordination/intervention_state.json");
  const state = readJson(path);
  if (!state?.interventions) { console.log("  · no intervention_state.json, skipping"); return; }

  const interventionIdByStateId = {};
  for (const [stateId, entry] of Object.entries(state.interventions)) {
    // derive country from verified_edge or first evidence country
    const country =
      entry.verified_edge?.country ||
      entry.evidence?.find((e) => e.country)?.country || null;
    const rec = await upsert("interventions", `stateId = "${stateId}"`, {
      stateId,
      country,
      blocker: entry.blocker ?? null,
      ownerPersona: entry.owner_persona ?? null,
      status: entry.status,
      evidence: entry.evidence ?? [],
      relatedSignals: entry.related_signals ?? [],
      verifiedEdge: entry.verified_edge ?? null,
      scoreChanges: entry.score_changes ?? null,
      createdAt: toDate(entry.created_at),
      verifiedAt: toDate(entry.verified_at),
      updatedAt: toDate(entry.updated_at),
    });
    if (rec) {
      synced.interventions++;
      interventionIdByStateId[stateId] = rec.id;
      // flatten nested outcomes
      for (const o of entry.outcomes ?? []) {
        const outcomeRec = await upsert(
          "outcomes",
          `intervention = "${rec.id}" && type = "${o.type}" && submittedAt = "${toDate(o.submitted_at)}"`,
          {
            intervention: rec.id,
            type: o.type,
            delta: OUTCOME_DELTA[o.type] ?? 0,
            note: o.note ?? "",
            submittedAt: toDate(o.submitted_at),
          }
        );
        if (outcomeRec) synced.outcomes++;
      }
    }
  }

  // campaigns (derived in coordination/interventions.py)
  if (state.campaigns) {
    for (const [slug, c] of Object.entries(state.campaigns)) {
      const rec = await upsert("campaigns", `slug = "${slug}"`, {
        slug,
        interventionCount: c.intervention_count ?? 0,
        activeCount: c.active_count ?? 0,
        ownerPersona: c.owner_persona ?? null,
        blocker: c.blocker ?? null,
        interventionType: c.intervention_type ?? null,
        interventionIds: c.interventions ?? [],
        updatedAt: toDate(c.updated_at),
      });
      if (rec) synced.campaigns++;
    }
  }
}

// Optional: watchers write data/<source>/latest.json — sync as sources/observations
async function syncSources() {
  const dataDir = resolve(SF_ROOT, "data");
  if (!existsSync(dataDir)) return;
  const sources = ["world_bank", "idb", "noaa_nws", "ndbc_buoys", "tenders", "caricom", "cdb", "nhc"];
  for (const name of sources) {
    const latest = readJson(resolve(dataDir, name, "latest.json"));
    if (!latest) continue;
    const rec = await upsert("sources", `name = "${name}"`, {
      name,
      status: "live",
      lastFetched: toDate(latest.fetched_at || latest.generated_at),
    });
    if (rec) synced.sources++;
    // observations: latest.signals[] if present
    const sigs = latest.signals || latest.observations || [];
    if (Array.isArray(sigs)) {
      for (const s of sigs.slice(0, 50)) { // cap to avoid huge syncs
        const fp = s.fingerprint || s.id || shortHash(s);
        const obs = await upsert(
          "observations",
          `source = "${rec.id}" && fingerprint = "${fp}"`,
          { source: rec.id, fingerprint: fp, period: s.period ?? null, value: s.value ?? null, payload: s }
        );
        if (obs) synced.observations++;
      }
    }
  }
}

// Optional: outbox packs → packs collection (keyed by fileName)
async function syncPacks() {
  const ob = readJson(resolve(SF_ROOT, "outbox/coordination_opportunities.json"));
  if (ob?.opportunities) {
    for (const opp of ob.opportunities) {
      const rec = await upsert("packs", `fileName = "${opp.id}.json"`, {
        kind: "opportunity_dispatch",
        fileName: `${opp.id}.json`,
        body: opp,
      });
      if (rec) synced.packs++;
    }
  }
}

// ---- run ---------------------------------------------------------------
try {
  await auth();
  console.log(`Syncing Abeng → PocketBase (${PB_URL})`);
  await syncInterventions();
  await syncSources();
  await syncPacks();
  console.log(`✅ sync complete: ${JSON.stringify(synced)}`);
} catch (e) {
  console.warn(`⚠ PocketBase sync skipped: ${e.message}`);
  console.warn("  The committed JSON remains the source of truth. Pipeline continues.");
  process.exit(0); // non-fatal: PB down should not break the 4h pipeline
}
