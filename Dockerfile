# The server serves the Astro build from dist/, which is gitignored and so is
# absent from any clean checkout. This image used to be Python-only and its one
# "generate the dashboard" step called dashboard/generate.py — deleted when the
# legacy UI was retired in July 2026, and masked by `|| true`. The container
# started cleanly and 404'd every page while /api/* answered normally. Build
# the site here so the image ships with a UI.
FROM node:22-slim AS site
WORKDIR /app
RUN npm install -g pnpm@10
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# Call Astro directly rather than `pnpm build`: same output, no lifecycle
# scripts that expect a TTY (scripts/verify.sh and playwright.config.ts do the
# same, for the same reason).
RUN node ./node_modules/astro/bin/astro.mjs build

FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=site /app/dist ./dist

ENV PORT=8080
EXPOSE 8080

CMD ["python3", "server.py"]
