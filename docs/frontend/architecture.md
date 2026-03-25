# Frontend Architecture

> Owner: @elena (Elena Vasquez, Senior Frontend Engineer)
> Last updated: 2026-03-25

---

## Technology Stack

| Layer           | Technology                          | Version   |
|-----------------|-------------------------------------|-----------|
| Framework       | Next.js (App Router)                | 14.2.x    |
| Language        | TypeScript (strict)                 | 5.6.x    |
| Runtime         | Node.js LTS                         | 20.x     |
| Styling         | Tailwind CSS                        | 3.4.x    |
| Components      | Radix UI (headless)                 | latest   |
| Server State    | React Query (TanStack Query)        | 5.x      |
| Client State    | Zustand                             | 5.x      |
| Forms           | React Hook Form + Zod              | 7.x / 3.x|
| Charts          | Recharts                            | 2.13.x   |
| Tables          | TanStack Table                      | 8.x      |
| Auth            | NextAuth.js                         | 5.x beta |
| Package Manager | pnpm                                | 9.x      |

---

## Rendering Strategy

Every component is a Server Component until there is a specific, documented
reason to make it a Client Component.

### Route-Level Decisions

```
Route                           Component Type      Rationale
-------------------------------+-------------------+----------------------------------
/                               Server Component    Redirect to /dashboard
/login                          Server Component    Static form shell
/login (LoginForm)              Client Component    useState, onSubmit, signIn()
/dashboard                      Server Component    Initial data fetch from BFF
/dashboard (CaseQueueTable)     Client Component    TanStack Table interactivity
/dashboard/cases/[id]           Server Component    SEO + initial load
/dashboard/cases/[id] (Gauge)   Client Component    Recharts DOM measurements
/api/risk/score                 Route Handler       BFF proxy to backend
/api/health                     Route Handler       Health check
```

### Valid Reasons for "use client"

A component gets "use client" ONLY if it requires one of:

1. Browser APIs (window, document, localStorage)
2. Event handlers (onClick, onChange, onSubmit)
3. React hooks that require client state (useState, useEffect, useRef)
4. Real-time updates / polling
5. Interactive mutations with optimistic UI

---

## BFF (Backend-for-Frontend) Pattern

```
                        Browser
                          |
                    [httpOnly cookie]
                          |
                    Next.js Server
                    (Route Handlers)
                          |
                    [server-side fetch]
                          |
                    FastAPI Backend
                    (port 8000)
```

### Security Constraints (agreed with @priya)

1. **No JWT in localStorage.** NextAuth.js manages sessions server-side.
   The browser holds an encrypted httpOnly cookie, not a JWT.

2. **BFF pattern mandatory.** All API calls from the browser go through
   Next.js Route Handlers (`/api/*`). The browser never calls the FastAPI
   backend directly.

3. **CSP: `script-src 'self'`** with nonce pattern. No inline scripts,
   no eval. Third-party scripts require @priya review.

4. **CSRF protection.** Route Handlers use `SameSite=Strict` cookies.

5. **Idempotency-Key forwarding.** The BFF Route Handler at `/api/risk/score`
   forwards the `Idempotency-Key` header from the client to the backend.

### Request Flow: POST /api/risk/score

```
1. Browser → POST /api/risk/score
   Headers: Idempotency-Key: <uuid>, Cookie: next-auth.session-token=<encrypted>
   Body: { transaction_id, customer_id, amount_cents, ... }

2. Route Handler:
   a. getServerSession() → verify auth (reject 401 if no session)
   b. Zod parse request body (reject 422 if invalid)
   c. fetch(BACKEND_URL/v1/risk/score) with Idempotency-Key header
   d. Zod parse backend response (reject 502 if shape mismatch)
   e. Return validated response to browser

3. Browser receives: { request_id, risk_score, risk_level, decision, ... }
```

---

## NextAuth.js Configuration

| Setting            | Value                                    |
|--------------------|------------------------------------------|
| Strategy           | JWT (encrypted in httpOnly cookie)       |
| Session maxAge     | 8 hours (analyst shift)                  |
| Dev provider       | Credentials (email/password mock)        |
| Prod provider      | Keycloak OIDC                            |
| Sign-in page       | /login                                   |

### Dev Credentials

| Role    | Email            | Password    |
|---------|------------------|-------------|
| Analyst | analyst@ras.dev  | analyst123  |
| Admin   | admin@ras.dev    | admin123    |

---

## Component Tree

```
RootLayout (Server)
├── Providers (Client) — SessionProvider + QueryClientProvider
│   └── children
│
├── /login
│   └── LoginPage (Server)
│       └── LoginForm (Client) — React Hook Form + signIn()
│
├── /dashboard
│   └── DashboardLayout (Server) — nav chrome
│       └── DashboardPage (Server) — fetches cases
│           └── CaseQueue (Server) — wrapper
│               └── CaseQueueTable (Client) — TanStack Table
│
├── /dashboard/cases/[id]
│   └── CaseDetailPage (Server) — fetches case data
│       ├── RiskScoreGauge (Client) — Recharts gauge
│       ├── RiskBadge (Server) — risk level badge
│       └── DecisionBadge (Server) — decision badge
│
└── /api/*
    ├── /api/auth/[...nextauth] — NextAuth handler
    ├── /api/risk/score — BFF scoring proxy
    └── /api/health — health check
```

---

## Bundle Size Budgets

Enforced in CI via `bundlewatch` in `package.json`.

| Route                  | Budget   | Notes                         |
|------------------------|----------|-------------------------------|
| Dashboard (case queue) | < 150KB  | TanStack Table + badges       |
| Rule editor            | < 300KB  | CodeMirror (future sprint)    |

Baselines will be established after the first production build and tracked
per-commit in CI.

---

## Accessibility Standards (WCAG 2.1 AA)

| Requirement                     | Implementation                              |
|---------------------------------|---------------------------------------------|
| Color contrast 4.5:1            | Tailwind palette in tailwind.config.ts      |
| Never color alone (1.4.1)       | Badges have text + directional indicators   |
| Focus management (2.4.3)        | Radix UI + custom focus rings               |
| Charts (role="img")             | RiskScoreGauge has descriptive aria-label    |
| Keyboard navigation             | All interactive elements keyboard-accessible|
| axe-core CI gate                | @axe-core/playwright in Playwright tests    |

---

## Type Safety

| Concern                 | Approach                                      |
|-------------------------|-----------------------------------------------|
| TypeScript config       | strict: true + noUncheckedIndexedAccess       |
| API response validation | Zod schemas at every network boundary         |
| API type generation     | Manual now; openapi-typescript in CI (future) |
| No `any`                | ESLint @typescript-eslint/no-explicit-any     |
| Form validation         | React Hook Form + Zod resolver                |

---

## Cross-Agent Alignment

| Agent    | Alignment                                                         |
|----------|-------------------------------------------------------------------|
| @sofia   | Types derived from Pydantic schemas. BFF forwards Idempotency-Key |
| @priya   | BFF pattern, CSP headers, no JWT in localStorage, httpOnly cookie |
| @darius  | Dockerfile multi-stage, docker-compose on ras_net, /api/health    |
| @aisha   | data-testid convention: [component]-[element]                     |
| @james   | GDPR UI (cookie consent, erasure flows) — future sprint           |
| @yuki    | ML monitoring dashboard consuming Evidently AI — future sprint    |
