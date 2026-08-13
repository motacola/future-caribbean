// Browser-safe PocketBase client for Signal Fabric frontend realtime.
// URL comes from the PUBLIC_PB_URL env (inlined at Astro build time).
// If unset, getPb() returns null and the realtime layer is a no-op (page renders
// from the committed-JSON build as before — zero regression).

import PocketBase from "./vendor/pocketbase.mjs";

let _pb: PocketBase | null = null;
let _unavailable = false;

export function getPb(): PocketBase | null {
  if (_unavailable) return null;
  const url = import.meta.env.PUBLIC_PB_URL as string | undefined;
  if (!url) {
    _unavailable = true;
    return null;
  }
  if (!_pb) {
    _pb = new PocketBase(url);
    _pb.autoCancellation(false);
  }
  return _pb;
}

export function pbEnabled(): boolean {
  return !!import.meta.env.PUBLIC_PB_URL;
}
