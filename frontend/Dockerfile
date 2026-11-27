# Frontend — TanStack Start
# Builder: Bun 1.4.2 · Runtime: Node 24.22.1 (sesuai permintaan)
# Context: root repo. Build stage di frontend/.

FROM oven/bun:1.4.2-alpine AS builder
WORKDIR /app/frontend

# Salin seluruh sumber agar postinstall (normalize-i18n-docs) dan frozen-lockfile
# menemukan semua file yang dibutuhkan, termasuk patches/.
COPY frontend/ .

RUN bun install --frozen-lockfile --no-cache && bun --bun run build

# Runtime: Node 24.22.1. node_modules disalin dari builder agar bare import
# (react, @tanstack/*, dll) di dist/server/server.js bisa di-resolve.
FROM node:24.22.1-alpine
WORKDIR /app/frontend

ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0

EXPOSE 3000

COPY --from=builder /app/frontend/package.json ./
COPY --from=builder /app/frontend/node_modules ./node_modules
COPY --from=builder /app/frontend/dist ./dist
COPY frontend/server.mjs ./server.mjs

# Non-root user untuk CKV_DOCKER_3 (node user sudah disediakan image).
RUN chown -R node:node /app/frontend
USER 1000:1000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:'+process.env.PORT+'/health/live').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]

# dist/server/server.js mengekspor handler fetch, bukan listener HTTP.
CMD ["node", "server.mjs"]
