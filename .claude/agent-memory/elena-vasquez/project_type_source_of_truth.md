---
name: TypeScript Type Source of Truth
description: Frontend types are manually maintained until OpenAPI CI pipeline is wired; must stay in sync with Pydantic schemas
type: project
---

TypeScript types in `frontend/src/types/ras-api.ts` are manually derived from @sofia's Pydantic schemas in `app/scoring/schemas.py`. The corresponding Zod schemas for runtime validation are in `frontend/src/lib/zod-schemas.ts`.

**Why:** @sofia has not yet published a stable OpenAPI spec for CI-based type generation. The `openapi-typescript` tool is configured in package.json (`pnpm generate:types`) but requires the backend to be running and the spec to be stable.

**How to apply:** Any change to backend Pydantic schemas MUST be reflected manually in both `ras-api.ts` (TypeScript types) and `zod-schemas.ts` (Zod runtime validation). Once the OpenAPI CI pipeline is wired, the manual types will be replaced by auto-generated ones, and schema drift will become a compile error.
