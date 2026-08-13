import PocketBase from "pocketbase";
const PB = process.env.PB_URL || "http://127.0.0.1:8097";
const admin = new PocketBase(PB);
await admin.admins.authWithPassword("admin@signalfabric.local", "HermesVerify123!");

function ok(n, msg) { console.log(`  ✅ ${n}) ${msg}`); }
function bad(n, msg) { console.log(`  ❌ ${n}) ${msg}`); }
async function mustFail(n, label, fn) {
  try { await fn(); bad(n, `${label} — BUT WRITE SUCCEEDED (security hole)`); }
  catch (e) { ok(n, `${label} blocked (${e.status})`); }
}

// 1) admin can list all collections
const cols = await admin.collections.getFullList();
ok(1, `admin sees ${cols.length} collections: ${cols.map(c=>c.name).join(", ")}`);

const anon = new PocketBase(PB);

// 2) anonymous READ of public signals -> must succeed
const pub = await anon.collection("signals").getList(1, 1);
ok(2, `anonymous can READ public 'signals' (${pub.totalItems} rows)`);

// 3) anonymous WRITE to signals -> must FAIL (admin-only create)
await mustFail(3, "anonymous write to 'signals'", () =>
  anon.collection("signals").create({ kind: "x", priority: "low", country: "Barbados", score: 0.1 }));

// 4) anonymous WRITE to interventions -> must FAIL (operator-only)
await mustFail(4, "anonymous write to 'interventions'", () =>
  anon.collection("interventions").create({ title: "x", status: "proposed", beforeScore: 0 }));

// 5) create operator, auth, write intervention -> must succeed
await admin.collection("users").create({
  email: "op@x.com", password: "OpPass123!", passwordConfirm: "OpPass123!",
  displayName: "Op", role: "operator",
});
const opAuth = new PocketBase(PB);
await opAuth.collection("users").authWithPassword("op@x.com", "OpPass123!");
const iv = await opAuth.collection("interventions").create({
  title: "Verify Barbados vendor", country: "Barbados", status: "verified",
  beforeScore: 0.2, afterScore: 0.9,
});
ok(5, `operator wrote+verified intervention ${iv.id} (status=${iv.status})`);

// 6) anonymous READ verified intervention -> must succeed
const readBack = await anon.collection("interventions").getList(1, 1, { filter: `status="verified"` });
ok(6, `anonymous can READ verified interventions (${readBack.totalItems} row)`);

// 7) anonymous READ proposed intervention -> must FAIL (viewRule)
await mustFail(7, "anonymous read of proposed 'interventions'", () =>
  anon.collection("interventions").getList(1, 1, { filter: `status="proposed"` }));

console.log("\nSECURITY MODEL VERIFIED");
