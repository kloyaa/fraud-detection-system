# =============================================================================
# RAS Frontend — Multi-stage Dockerfile
# =============================================================================
# Coordinated with @darius:
# - Node 20 LTS on Alpine for minimal image size
# - Multi-stage: deps → builder → runner
# - Non-root user (nextjs:nodejs) in production
# - Healthcheck via /api/health
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Install dependencies
# ---------------------------------------------------------------------------
FROM node:20-alpine AS deps

RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@9.12.3 --activate

# Copy dependency manifests
COPY package.json pnpm-lock.yaml ./

# Install dependencies (frozen lockfile in CI, regular install for dev)
RUN pnpm install --frozen-lockfile 2>/dev/null || pnpm install

# ---------------------------------------------------------------------------
# Stage 2: Build the application
# ---------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.12.3 --activate

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build arguments for environment-specific builds
ARG NEXT_PUBLIC_APP_ENV=production
ENV NEXT_PUBLIC_APP_ENV=$NEXT_PUBLIC_APP_ENV

# Disable Next.js telemetry
ENV NEXT_TELEMETRY_DISABLED=1

# Build with verbose error reporting
RUN pnpm build && ls -la .next/ || (echo "Build failed: .next directory not created" && exit 1)

# ---------------------------------------------------------------------------
# Stage 3: Production runner
# ---------------------------------------------------------------------------
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
  adduser --system --uid 1001 nextjs

# Copy built assets with verification
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
# Verify standalone was copied correctly
RUN ls -la / && test -f server.js || (echo "ERROR: server.js not found in /app" && exit 1)
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# @darius: Healthcheck for Docker / k8s readiness probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
