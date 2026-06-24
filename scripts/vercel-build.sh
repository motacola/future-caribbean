#!/usr/bin/env bash
set -e

if [ "$VERCEL_PROJECT_NAME" = "future-caribbean" ]; then
  echo "▶ future-caribbean: building holding page"
  mkdir -p dist
  cp scripts/future-caribbean-holding.html dist/index.html
  echo "✓ done"
else
  echo "▶ signal-fabric: building full site"
  pnpm install
  pnpm build
fi
