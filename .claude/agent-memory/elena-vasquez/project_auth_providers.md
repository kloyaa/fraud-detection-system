---
name: Auth Provider Configuration
description: Credentials provider is dev-only; Keycloak OIDC in staging/prod -- agreed with @priya
type: project
---

NextAuth.js is configured with a Credentials provider for local development only. This provider uses hardcoded mock users (analyst@ras.dev / analyst123, admin@ras.dev / admin123).

In staging and production, the Credentials provider MUST be replaced with Keycloak OIDC. The environment variables `KEYCLOAK_ISSUER`, `KEYCLOAK_CLIENT_ID`, and `KEYCLOAK_CLIENT_SECRET` are templated in `.env.local.example`.

**Why:** Credentials provider has no MFA, no account lockout, no password policy. It exists solely to unblock frontend development before the Keycloak instance is provisioned. Agreed with @priya that this is acceptable for dev, not for staging/prod.

**How to apply:** When wiring Keycloak, add it as an additional provider in `frontend/src/lib/auth.ts` and conditionally exclude the Credentials provider when `NEXT_PUBLIC_APP_ENV !== 'development'`. Session maxAge remains 8 hours (analyst shift length).
