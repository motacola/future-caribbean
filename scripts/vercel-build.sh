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

  # Copy files that live outside Astro's output but are served as static
  cp outbox/feed.xml   dist/feed.xml   2>/dev/null || true
  cp llms.txt          dist/llms.txt   2>/dev/null || true
  cp agents.md         dist/agents.md  2>/dev/null || true
  mkdir -p dist/data/history
  cp -r data/history/. dist/data/history/ 2>/dev/null || true

  echo "✓ done"
fi
