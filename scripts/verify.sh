#!/usr/bin/env bash
# Verification gate. Replaces the build/test/check sequence that was previously
# retyped by hand each time.
#
#   scripts/verify.sh          # everything
#   scripts/verify.sh fast     # skip the browser tests
#   scripts/verify.sh data     # data integrity only: no Node toolchain needed
#
# `data` is what the scheduled pipeline runs before it commits. That workflow
# publishes data artefacts, not the site — Vercel builds the site from the
# committed data on its own — so gating the commit needs pytest, the ranking
# invariants and the ledger chain, and does not need Astro or a browser.
#
# Exits non-zero on the first failure so it can gate CI.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MODE="${1:-}"
FAILED=()

# The codebase uses PEP 604 unions (`float | None`), so it needs 3.10+. This
# used to hardcode /usr/bin/python3, which on macOS is 3.9 — the gate failed at
# test collection for anyone who ran it, while CI ran 3.12 and passed. Resolve
# an interpreter new enough to import the package instead of assuming a path.
PY=""
for candidate in "${PYTHON:-}" python3 python3.13 python3.12 python3.11 /usr/bin/python3; do
  [ -n "$candidate" ] || continue
  command -v "$candidate" >/dev/null 2>&1 || continue
  if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    PY="$candidate"; break
  fi
done
if [ -z "$PY" ]; then
  echo "No Python 3.10+ found. Set PYTHON=/path/to/python3 and re-run." >&2
  exit 1
fi
printf '%-22s%s\n' "interpreter" "$($PY -V 2>&1) at $(command -v "$PY")"

step() {
  local label="$1"; shift
  printf '%-22s' "$label"
  local out
  if out=$("$@" 2>&1); then
    echo "ok    $(echo "$out" | tail -1 | cut -c1-60)"
  else
    echo "FAIL"
    echo "$out" | tail -15 | sed 's/^/    /'
    FAILED+=("$label")
  fi
}

# Artefacts a verification run must never alter. Checked, not overwritten: this
# previously ran `git checkout --` on them unconditionally, which silently
# discarded whatever uncommitted pipeline output happened to be in the tree.
GUARDED=(api/feedback-data.json data/coordination/graph.json
         outbox/coordination_opportunities.json outbox/track_record.json)
guard_digest() {
  local f out=""
  for f in "${GUARDED[@]}"; do
    [ -e "$f" ] && out+="$f:$($PY -c "
import hashlib,sys
print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())
" "$f") "
  done
  echo "$out"
}
GUARD_BEFORE="$(guard_digest)"

if [ "$MODE" != "data" ]; then
  # `pnpm build` runs pnpm install, which aborts without a TTY and wants to
  # purge node_modules. Call Astro directly.
  step "build"        node ./node_modules/astro/bin/astro.mjs build
fi

step "python tests" env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 DISABLE_PIPELINE_LOOP=1 "$PY" -m pytest tests/ -q
step "ranking"      "$PY" scripts/verify_ranking.py
step "ledger chain" "$PY" -c "
import sys, json, pathlib
sys.path.insert(0, '.')
from packagers.calibration import verify_chain
p = pathlib.Path('data/calibration/ledger.json')
if not p.exists():
    print('no ledger yet'); raise SystemExit(0)
ok, at = verify_chain(json.loads(p.read_text()))
print('intact' if ok else f'BROKEN at claim {at}')
raise SystemExit(0 if ok else 1)
"

if [ "$MODE" != "fast" ] && [ "$MODE" != "data" ]; then
  step "browser tests" npx playwright test
  rm -rf test-results
fi

# Report drift rather than reverting it. As of 2026-09-04 nothing in the run
# touches these — pytest, the ranking check, the Astro build and the 56 browser
# tests were each measured against them — so drift here means something new
# started writing to a published artefact, which is worth failing on.
printf '%-22s'  "artefacts"
if [ "$(guard_digest)" = "$GUARD_BEFORE" ]; then
  echo "ok    unchanged by this run"
else
  echo "FAIL"
  echo "    a check wrote to a published artefact; inspect with 'git diff'"
  FAILED+=("artefacts")
fi

echo
if [ ${#FAILED[@]} -gt 0 ]; then
  echo "FAILED: ${FAILED[*]}"
  exit 1
fi
echo "All checks passed."
