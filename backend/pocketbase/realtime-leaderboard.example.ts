// Example Astro client island: realtime Abeng map + desk.
// Drop into a <script> island on regional-connections.astro / /build desk.
// Requires: npm i @pocketbase/js  and PB CORS allowing your Vercel origin.

import PocketBase from "@pocketbase/js";

const PB_URL = import.meta.env.PUBLIC_PB_URL ?? "https://pb.yourhost.com";
const pb = new PocketBase(PB_URL);

// Keep auth (operator desk writes). Anonymous reads still work via viewRule.
pb.authStore.loadFromCookie(document.cookie);

type Unsub = () => Promise<void>;

const unsubs: Unsub[] = [];

async function initRealtime() {
  // 1) Live leaderboard / map: any signal change updates markers instantly.
  unsubs.push(
    await pb.collection("signals").subscribe("*", (e) => {
      if (e.action === "create" || e.action === "update") {
        updateMapMarker(e.record);   // your existing marker render fn
      } else if (e.action === "delete") {
        removeMapMarker(e.record.id);
      }
    })
  );

  // 2) Operator desk: surface verified interventions the moment they're verified.
  unsubs.push(
    await pb.collection("interventions").subscribe("verified", (e) => {
      if (e.action === "create" || e.action === "update") {
        prependDeskCard(e.record);   // your existing desk render fn
      }
    })
  );
}

// Operator action: verify an intervention (requires operator auth).
async function verifyIntervention(id: string, afterScore: number, edges: unknown[]) {
  await pb.collection("interventions").update(id, {
    status: "verified",
    afterScore,
    capabilityEdges: edges,
    verifiedAt: new Date().toISOString(),
  });
  // All subscribed clients (including this one) get the push automatically.
}

function cleanup() {
  for (const u of unsubs) u();
}

document.addEventListener("astro:page-load", initRealtime);
document.addEventListener("astro:before-swap", cleanup);

// --- your existing renderers (stubs to show the contract) ---
function updateMapMarker(_r: Record<string, unknown>) {}
function removeMapMarker(_id: string) {}
function prependDeskCard(_r: Record<string, unknown>) {}
