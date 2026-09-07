#!/usr/bin/env bash
set -e

echo "▶ building full site"
pnpm install

# Regional news data (data/regional_news/latest.json) is force-committed to git and
# refreshed by the cron pipeline locally, then force-added + deployed. We do NOT
# re-poll here: Vercel's build sandbox has unreliable RSS egress and would overwrite
# the good committed data with an empty/partial result. map_data.py / src/lib/data.ts
# read this file at build time, so the committed copy is what ships.
# Belt-and-suspenders: also copy it into public/ so it is guaranteed present in the
# deploy tree regardless of .gitignore / .vercelignore edge cases.
echo "▶ using committed regional news data (no in-build polling)"
mkdir -p public
cp data/regional_news/latest.json public/regional_news.json
cp data/regional_news/latest.json api/regional-news-data.json
node scripts/news-thumbnails.mjs

pnpm build

# Copy files that live outside Astro's output but are served as static
cp outbox/feed.xml   dist/feed.xml   2>/dev/null || true
cp llms.txt          dist/llms.txt   2>/dev/null || true
cp agents.md         dist/agents.md  2>/dev/null || true
mkdir -p dist/data/history
cp -r data/history/. dist/data/history/ 2>/dev/null || true

echo "✓ done"
