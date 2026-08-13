// Signal Fabric — realtime desk enhancement (additive, zero-regression).
//
// Connects to PocketBase (if PUBLIC_PB_URL is set) and live-updates a dedicated
// feed container. It NEVER mutates the build-time-rendered cards — it only
// appends verified interventions / signal updates into #pb-live-feed. If PB is
// down or the env is unset, the container stays empty and the page is identical
// to the committed-JSON build.
//
// Wire it from a page with:
//   <div id="pb-live-feed" class="pb-live-feed" aria-live="polite"></div>
//   <script>import "../scripts/desk-realtime.ts";</script>

import { getPb, pbEnabled } from "../lib/pocketbase.ts";

const FEED_SEL = "#pb-live-feed";

function el(html: string): HTMLElement {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild as HTMLElement;
}

function renderItem(rec: any): HTMLElement {
  const title = rec.blocker
    ? `${rec.country || "Caribbean"} — unlock ${rec.blocker}`
    : (rec.stateId || "Intervention");
  const status = rec.status || "verified";
  return el(`
    <div class="pb-live-item" data-pb-id="${rec.stateId ?? rec.id}">
      <span class="pb-live-dot" data-status="${status}"></span>
      <div class="pb-live-body">
        <strong>${title}</strong>
        <span class="pb-live-meta">${status} · just now</span>
      </div>
    </div>
  `);
}

function upsertItem(feed: HTMLElement, rec: any) {
  const id = rec.stateId ?? rec.id;
  const existing = feed.querySelector(`[data-pb-id="${CSS.escape(id)}"]`);
  const node = renderItem(rec);
  if (existing) existing.replaceWith(node);
  else feed.prepend(node);
}

export async function initRealtime() {
  if (!pbEnabled()) return;            // no-op without env
  const pb = getPb();
  if (!pb) return;

  const feed = document.querySelector<HTMLElement>(FEED_SEL);
  if (!feed) return;                   // page has no feed container — skip

  feed.innerHTML = `<div class="pb-live-head">Live · verified interventions</div>`;

  try {
    // Seed with current verified interventions (so the feed isn't empty on load)
    const seed = await pb.collection("interventions").getList(1, 50, {
      filter: "status = 'verified'",
      sort: "-verifiedAt",
    });
    for (const rec of seed.items) upsertItem(feed, rec);

    // Subscribe to verified interventions → instant desk updates on operator verify
    await pb.collection("interventions").subscribe("verified", (e: { action: string; record: any }) => {
      if (e.action === "create" || e.action === "update") upsertItem(feed, e.record);
    });

    // Optional: live signal ticks (map/leaderboard)
    await pb.collection("signals").subscribe("*", (e: { action: string; record: any }) => {
      if (e.action === "create" || e.action === "update") {
        document.dispatchEvent(new CustomEvent("pb:signal", { detail: e.record }));
      }
    });
  } catch (err) {
    // PB unreachable — leave the feed empty, page still fully works from build JSON
    console.warn("[signal-fabric] PocketBase realtime unavailable:", (err as Error)?.message);
    feed.innerHTML = "";
  }
}

// Run after DOM ready (Astro islands load at end of body)
if (document.readyState === "loading") {
  document.addEventListener("astro:page-load", initRealtime);
  document.addEventListener("DOMContentLoaded", initRealtime);
} else {
  initRealtime();
}
