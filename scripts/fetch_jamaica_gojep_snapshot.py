#!/usr/bin/env python3
"""Refresh Jamaica GOJEP HTML snapshots (stdlib HTTP).

Runs the same fetch path as the pipeline adapter. Use browser-harness only
when GOJEP starts blocking plain HTTP again:

  browser-harness <<'PY'
  new_tab("https://www.gojep.gov.jm/epps/common/viewOpenedTenders.do")
  wait_for_load()
  # save page HTML to data/tenders/raw/jamaica-gojep-opened-YYYYMMDD.html
  PY
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from watchers.tenders.jamaica_gojep import JamaicaGojepAdapter  # noqa: E402


def main() -> int:
    items = JamaicaGojepAdapter().fetch()
    print(f"Jamaica GOJEP: {len(items)} normalized records")
    return 0 if items else 1


if __name__ == "__main__":
    raise SystemExit(main())
