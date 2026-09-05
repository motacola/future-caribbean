import PocketBase from "pocketbase";
const PB = process.env.PB_URL || "http://127.0.0.1:8097";
const admin = new PocketBase(PB);
await admin.admins.authWithPassword("admin@abeng.local", "HermesVerify123!");
const anon = new PocketBase(PB);

// operator session
const op = new PocketBase(PB);
await op.collection("users").authWithPassword("op@x.com", "OpPass123!");

// create a PROPOSED intervention with sensitive content
const prop = await op.collection("interventions").create({
  title: "SECRET pending vendor (Barbados)", country: "Barbados",
  status: "proposed", beforeScore: 0.1, afterScore: 0,
});
console.log(`created proposed intervention ${prop.id}`);

// anonymous fetches ALL interventions (no status filter)
const all = await anon.collection("interventions").getFullList();
const ids = all.map(r => r.id);
const sawProposed = ids.includes(prop.id);
const onlyVerified = all.every(r => r.status === "verified");

console.log(`anonymous sees ${all.length} intervention(s): ${ids.join(", ")}`);
console.log(`proposed id = ${prop.id}`);

if (sawProposed) {
  console.log("  ❌ SECURITY HOLE: anonymous can READ a proposed (non-verified) intervention");
} else {
  console.log("  ✅ anonymous CANNOT read proposed interventions (viewRule enforced)");
}
if (onlyVerified && all.length >= 1) {
  console.log("  ✅ anonymous only sees verified interventions");
} else {
  console.log("  ❌ unexpected: anonymous sees non-verified records");
}

// cleanup the proposed record so it doesn't pollute later runs
await admin.collection("interventions").delete(prop.id);
console.log("cleaned up test proposed record");
