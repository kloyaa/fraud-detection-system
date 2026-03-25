# Frontend — Getting Started

> Owner: @elena (Elena Vasquez, Senior Frontend Engineer)
> Last updated: 2026-03-25

---

## Prerequisites

- Node.js 20 LTS (required)
- pnpm 9.x (`corepack enable && corepack prepare pnpm@9.12.3 --activate`)
- Docker + Docker Compose (for full-stack development)

---

## Option 1: Docker (Recommended)

Run the full stack — backend + frontend + databases — with a single command.

```bash
# From project root
make docker-up
```

This starts:
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`
- FastAPI backend on `localhost:8000`
- Next.js frontend on `localhost:3000`

The frontend dev server hot-reloads on file changes (source is volume-mounted).

### Verify

```bash
# Backend health
curl http://localhost:8000/v1/health

# Frontend health (includes backend connectivity check)
curl http://localhost:3000/api/health

# Open dashboard
open http://localhost:3000
```

---

## Option 2: Local Development (without Docker)

If you prefer running the frontend outside Docker (faster HMR, direct debugging):

### 1. Start the backend

```bash
# From project root
make docker-up
# OR
make dev
```

### 2. Install frontend dependencies

```bash
# From project root
make frontend-install
# OR
cd frontend && pnpm install
```

### 3. Configure environment

```bash
cd frontend
cp .env.local.example .env.local
# Edit .env.local:
#   BACKEND_URL=http://localhost:8000  (local backend)
#   NEXTAUTH_SECRET=<generate with: openssl rand -base64 32>
#   NEXTAUTH_URL=http://localhost:3000
```

### 4. Start the dev server

```bash
make frontend-dev
# OR
cd frontend && pnpm dev
```

The dashboard is now available at `http://localhost:3000`.

---

## Development Credentials

| Role    | Email            | Password    |
|---------|------------------|-------------|
| Analyst | analyst@ras.dev  | analyst123  |
| Admin   | admin@ras.dev    | admin123    |

These credentials work with the dev-only Credentials provider. In staging/prod,
authentication uses Keycloak OIDC (configured via environment variables).

---

## Environment Variables

| Variable                | Required | Default | Description                            |
|-------------------------|----------|---------|----------------------------------------|
| `NEXT_PUBLIC_APP_ENV`   | No       | -       | "development" or "production"          |
| `NEXTAUTH_SECRET`       | Yes      | -       | Session encryption key (openssl rand)  |
| `NEXTAUTH_URL`          | Yes      | -       | Canonical URL (http://localhost:3000)  |
| `BACKEND_URL`           | Yes      | -       | FastAPI backend URL (server-side only) |
| `KEYCLOAK_ISSUER`       | Prod     | -       | Keycloak realm URL                     |
| `KEYCLOAK_CLIENT_ID`    | Prod     | -       | OIDC client ID                         |
| `KEYCLOAK_CLIENT_SECRET`| Prod     | -       | OIDC client secret                     |

**Security note:** `BACKEND_URL` has no `NEXT_PUBLIC_` prefix — it is server-side only
and never exposed to the browser. This is intentional (BFF pattern).

---

## Available Commands

From the project root:

```bash
make frontend-dev         # Start Next.js dev server
make frontend-build       # Production build
make frontend-install     # Install dependencies
make frontend-lint        # ESLint + TypeScript check
make frontend-typecheck   # TypeScript type checking only
```

From `frontend/`:

```bash
pnpm dev                  # Dev server (port 3000)
pnpm build                # Production build
pnpm lint                 # ESLint + tsc --noEmit
pnpm typecheck            # tsc --noEmit
pnpm generate:types       # Regenerate types from OpenAPI spec
pnpm test                 # Jest unit tests
pnpm test:e2e             # Playwright E2E tests
pnpm test:a11y            # Playwright accessibility tests
pnpm storybook            # Storybook dev server (port 6006)
```

---

## Regenerating OpenAPI Types

Once @sofia publishes the stable OpenAPI spec, TypeScript types can be
auto-generated from the backend's OpenAPI JSON:

```bash
# Backend must be running
cd frontend
pnpm generate:types
```

This runs `openapi-typescript` against `http://localhost:8000/openapi.json`
and outputs to `src/types/generated-api.ts`.

Until the CI pipeline for type generation is wired, types in
`src/types/ras-api.ts` are maintained manually and must stay in sync
with the Pydantic schemas in `app/scoring/schemas.py`.

---

## Project Structure

```
frontend/
├── package.json               Dependencies and scripts
├── tsconfig.json              TypeScript strict config
├── tailwind.config.ts         Tailwind with WCAG-compliant color palette
├── next.config.ts             CSP headers, security config
├── .env.local.example         Environment variables template
├── Dockerfile                 Multi-stage production build
├── src/
│   ├── app/                   Next.js App Router pages
│   │   ├── layout.tsx         Root layout (Server Component)
│   │   ├── providers.tsx      Client providers (SessionProvider, QueryClient)
│   │   ├── page.tsx           Redirect to /dashboard
│   │   ├── (auth)/login/      Login page
│   │   ├── dashboard/         Analyst dashboard
│   │   │   ├── page.tsx       Case queue (Server Component)
│   │   │   └── cases/[id]/    Case detail (Server Component)
│   │   └── api/               BFF Route Handlers
│   │       ├── auth/          NextAuth handler
│   │       ├── risk/score/    Scoring proxy to backend
│   │       └── health/        Health check
│   ├── components/
│   │   ├── ui/                Design system primitives
│   │   └── dashboard/         Dashboard-specific components
│   ├── lib/
│   │   ├── auth.ts            NextAuth config
│   │   ├── api-client.ts      Typed API client (server + client)
│   │   ├── zod-schemas.ts     Runtime validation schemas
│   │   └── cn.ts              Tailwind class merge utility
│   └── types/
│       └── ras-api.ts         TypeScript types (from Pydantic schemas)
└── public/                    Static assets
```

---

## Testing

### Unit Tests (Jest + React Testing Library)

```bash
cd frontend && pnpm test
```

### E2E Tests (Playwright)

```bash
cd frontend && pnpm test:e2e
```

Requires the full stack running (backend + frontend).

### Accessibility Tests (axe-core)

```bash
cd frontend && pnpm test:a11y
```

Runs `@axe-core/playwright` on all pages. Violations are CI failures.

### data-testid Convention

Agreed with @aisha: `[component]-[element]`

| data-testid                  | Component         |
|------------------------------|-------------------|
| `risk-badge-level`           | RiskBadge         |
| `decision-badge-action`      | DecisionBadge     |
| `case-queue-table`           | CaseQueueTable    |
| `case-queue-row`             | CaseQueueTable    |
| `case-queue-cell-transaction`| CaseQueueTable    |
| `case-queue-cell-score`      | CaseQueueTable    |
| `case-queue-cell-level`      | CaseQueueTable    |
| `case-queue-cell-decision`   | CaseQueueTable    |
| `risk-score-gauge`           | RiskScoreGauge    |
| `login-form`                 | LoginForm         |
| `login-email`                | LoginForm         |
| `login-password`             | LoginForm         |
| `login-submit`               | LoginForm         |
| `login-error`                | LoginForm         |
| `skeleton-loader`            | Skeleton          |
| `case-queue-skeleton`        | CaseQueueSkeleton |
| `dashboard-error`            | DashboardError    |
| `dashboard-error-retry`      | DashboardError    |
| `case-detail-page`           | CaseDetailPage    |
| `case-detail-fields`         | CaseDetailPage    |
| `case-detail-reason-codes`   | CaseDetailPage    |
