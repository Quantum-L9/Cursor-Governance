FROM node:22-alpine AS builder

WORKDIR /app
# npm is the canonical package manager for this repo (committed package-lock.json,
# .npmrc scopes @quantum-l9 to GitHub Packages). Explicit COPY (no glob) avoids
# pulling unintended files into the image. `--ignore-scripts` blocks dependency
# lifecycle scripts (the project defines none).
COPY package.json package-lock.json .npmrc ./
RUN npm ci --ignore-scripts --no-audit --no-fund

COPY tsconfig.json ./
COPY src/ ./src/
RUN npm run build

# ─── Production Stage ───────────────────────────────────────────
FROM node:22-alpine AS production

WORKDIR /app
RUN apk add --no-cache curl tini

COPY package.json package-lock.json .npmrc ./
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund

COPY --from=builder /app/dist ./dist
COPY config/ ./config/

RUN mkdir -p /app/data/reports /app/data/assets /app/logs

USER node

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["node", "dist/index.js"]

EXPOSE 3100

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:3100/health || exit 1
