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

---

## CI/CD

`@darius` leads

```
[ ] GitHub Actions — lint, test, build, scan pipelines
[ ] ArgoCD installed on EKS
[ ] ECR registries created
[ ] Trivy + Snyk + Bandit integrated in CI
[ ] doc_status_check.yml workflow active
```

---

## Local Development

`@darius` leads

```
[ ] docker-compose.yml — full local stack
      postgres, cassandra, redis, kafka, vault, keycloak
[ ] .env.example with all required variables
[ ] make dev — one command to start everything
```

---

## Backend Foundation

`@sofia` leads

```
[ ] FastAPI app skeleton — routers, middleware, lifespan
[ ] SQLAlchemy async setup + asyncpg
[ ] Alembic migrations initialized
[ ] structlog configured
[ ] Health endpoints — /health/live + /health/ready
[ ] Pydantic v2 settings (environment config)
[ ] pytest + pytest-asyncio configured
[ ] Testcontainers conftest.py (PostgreSQL + Redis + Kafka)
```

---

## Frontend Foundation

`@elena` leads

```
[ ] Next.js App Router structure confirmed
[ ] TypeScript strict mode configured
[ ] Tailwind + Radix UI installed
[ ] NextAuth.js v5 + Keycloak OIDC wired
[ ] OpenAPI type generation script (openapi-typescript)
[ ] React Query v5 configured
[ ] Playwright + axe-core configured
[ ] Storybook initialized
[ ] CSP headers in next.config.ts
```

---

## Completion Criteria

✅ Sprint 0 done when:
- `make dev` starts the full stack locally
- CI passes on empty app
- Every engineer can run tests

---

**Owner:** Darius Okafor (`@darius`)  
**Status:** ⏳ Not started  
**Created:** 2026-03-25
