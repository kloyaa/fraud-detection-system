---
name: BFF Pattern Implementation
description: How the frontend BFF Route Handlers proxy requests to the FastAPI backend, including Idempotency-Key forwarding and Zod validation
type: project
---

The frontend enforces a strict BFF (Backend-for-Frontend) pattern. The browser NEVER calls the FastAPI backend directly.

**Route Handler at `/api/risk/score`:**
1. Authenticates via `getServerSession()` (NextAuth) -- rejects 401 if no session
2. Validates `Idempotency-Key` header is present -- rejects 400 if missing
3. Validates request body with `RiskScoreRequestSchema` (Zod) -- rejects 422 if invalid
4. Forwards to `BACKEND_URL/v1/risk/score` with the `Idempotency-Key` header
5. Validates backend response with `RiskScoreResponseSchema` (Zod) -- rejects 502 if shape mismatch
6. Returns validated response to browser

**Why:** Agreed with @priya -- no JWT in localStorage, no direct backend calls from browser. The BFF adds authentication, request validation, and response validation at every boundary.

**How to apply:** Every new backend endpoint must have a corresponding BFF Route Handler at `/api/*`. The browser must never be given the BACKEND_URL. All server-side fetch calls use the `serverScoreTransaction()` / `serverHealthCheck()` functions in `api-client.ts`.
