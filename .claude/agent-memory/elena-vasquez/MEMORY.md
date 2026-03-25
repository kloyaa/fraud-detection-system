# Memory Index

## Project Context
- [BFF Pattern Implementation](project_bff_pattern.md) — Route Handler proxy to FastAPI, Idempotency-Key forwarding, Zod validation at every boundary
- [TypeScript Type Source of Truth](project_type_source_of_truth.md) — Manual types until OpenAPI CI pipeline is wired; must sync with Pydantic schemas
- [data-testid Naming Convention](project_data_testid_convention.md) — [component]-[element] format agreed with @aisha, full ID registry
- [CSP Implementation](project_csp_implementation.md) — script-src self, no inline, nonce planned; agreed with @priya
- [Bundle Size Baselines](project_bundle_size_baselines.md) — Budgets set (150KB dashboard, 300KB rule editor); baselines pending first build
- [Auth Provider Configuration](project_auth_providers.md) — Credentials dev-only, Keycloak OIDC in staging/prod; agreed with @priya
