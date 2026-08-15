#!/usr/bin/env bash
# Full verification gate. Replaces the build/test/check sequence that was
# previously retyped by hand each time.
#
#   scripts/verify.sh          # everything
#   scripts/verify.sh fast     # skip the browser tests
#
# Exits non-zero on the first failure so it can gate CI.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
FAST="${1:-}"
FAILED=()

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

# `pnpm build` runs pnpm install, which aborts without a TTY and wants to
# purge node_modules. Call Astro directly.
step "build"        node ./node_modules/astro/bin/astro.mjs build
step "python tests" env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /usr/bin/python3 -m pytest tests/ -q
step "ranking"      /usr/bin/python3 scripts/verify_ranking.py
step "ledger chain" /usr/bin/python3 -c "
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

if [ "$FAST" != "fast" ]; then
  step "browser tests" npx playwright test
  rm -rf test-results
fi

# The suite rewrites tracked artefacts. Until that is fixed, restore them so a
# verification run never changes what the site publishes.
RESTORED=$(git checkout -- api/feedback-data.json data/coordination/graph.json \
  outbox/coordination_opportunities.json outbox/track_record.json 2>&1 && echo "restored")
printf '%-22s%s\n' "artefacts" "${RESTORED:-clean}"

echo
if [ ${#FAILED[@]} -gt 0 ]; then
  echo "FAILED: ${FAILED[*]}"
  exit 1
fi
echo "All checks passed."
