# Sprint 0 — Infrastructure & DevOps Foundation

**Goal:** Every engineer can run the full stack locally. CI/CD pipeline is live.

**Duration:** 2 weeks  
**Lead:** `@darius`  
**Supporting:** `@sofia`, `@elena`

---

## Infrastructure

`@darius` leads

```
[ ] Terraform — AWS account, VPC, subnets, IAM roles
[ ] EKS cluster provisioned (staging environment first)
[ ] Kafka cluster (Confluent Cloud — staging)
[ ] PostgreSQL RDS instance (staging)
[ ] Cassandra cluster (staging — 3 nodes)
[ ] Redis Cluster (staging — 3 nodes)
[ ] HashiCorp Vault (staging)
[ ] Keycloak (staging)
```

> Cloud provisioning requires AWS credentials — tracked separately.

---

## CI/CD

`@darius` leads

```
[x] GitHub Actions — lint, test, build, scan pipelines (.github/workflows/ci.yml)
[ ] ArgoCD installed on EKS
[ ] ECR registries created
[x] Trivy + Bandit integrated in CI
[x] doc_status_check.yml workflow active
```

---

## Local Development

`@darius` leads

```
[x] docker-compose.yml — full local stack
      postgres, cassandra, redis, kafka (KRaft), vault, keycloak
[x] .env.example with all required variables
[x] make dev — one command to start everything (docker-compose up -d)
```

---

## Backend Foundation

`@sofia` leads

```
[x] FastAPI app skeleton — routers, middleware, lifespan
[x] SQLAlchemy async setup + asyncpg
[x] Alembic migrations initialized
[x] structlog configured
[x] Health endpoints — /health/live + /health/ready
[x] Pydantic v2 settings (environment config)
[x] pytest + pytest-asyncio configured
[x] Testcontainers conftest.py (PostgreSQL + Redis + Kafka)
```

---

## Frontend Foundation

`@elena` leads

```
[x] Next.js App Router structure confirmed
[x] TypeScript strict mode configured
[x] Tailwind + Radix UI installed
[x] NextAuth.js v5 + Keycloak OIDC wired (+ dev credentials fallback)
[x] OpenAPI type generation script (openapi-typescript)
[x] React Query v5 configured
[x] Playwright + axe-core configured
[x] Storybook initialized (run: pnpm install && pnpm storybook)
[x] CSP headers in next.config.js
```

---

## Completion Criteria

✅ Sprint 0 done when:
- `make dev` starts the full stack locally
- CI passes on empty app
- Every engineer can run tests

---

**Owner:** Darius Okafor (`@darius`)
**Status:** ✅ Local dev complete — cloud provisioning pending AWS credentials
**Created:** 2026-03-25
**Completed:** 2026-03-25
