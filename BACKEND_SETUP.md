# Production-Grade Backend Foundation — Setup & Deployment Guide

> Risk Assessment System (RAS) v1.0.0  
> Backend Foundation: FastAPI + PostgreSQL + Redis + Alembic  
> **Status:** Implementation ready for Sprint 1

---

## What Was Built

A complete, runnable production foundation for the RAS fraud detection backend:

- ✅ **FastAPI application** with lifespan management, middleware, structured logging
- ✅ **Database layer** (SQLAlchemy 2.0 async + asyncpg + Alembic migrations)
- ✅ **Structured logging** (structlog → JSON)
- ✅ **Health endpoint** (`GET /v1/health`)
- ✅ **Idempotency middleware** (enforces Idempotency-Key header on POST/PATCH)
- ✅ **Scoring endpoint skeleton** (`POST /v1/risk/score`)
- ✅ **Test infrastructure** (pytest + Testcontainers + fixtures)
- ✅ **Lint/type-check pipeline** (Ruff + mypy strict mode)
- ✅ **Development tooling** (Makefile, docker-compose, pre-commit hooks)

---

## Implementation Sequence

### Phase 1: Dependencies & Environment (15 min)

**Option A: Docker (Recommended)**

```bash
# 1. Clone repo
git clone <repo_url>
cd fraud-detection-system

# 2. Start full stack (includes Python dependencies)
make docker-up

# 3. Verify all services healthy
docker-compose ps
```

**Option B: Local Python Environment**

```bash
# 1. Create venv
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
make install

# 3. Copy environment file
cp .env.example .env

# 4. Start database services (Docker)
docker-compose up -d postgres redis
```

### Phase 2: Validate Database Connectivity (5 min)

```bash
# Via Docker
docker-compose exec app alembic current

# Or locally
alembic current
```

### Phase 3: Run Tests (10 min)

```bash
# Via Docker (includes Testcontainers for PostgreSQL + Redis)
make docker-test

# Or locally (requires Python environment + Docker for Testcontainers)
make test-integration

# Expected: ✅ 5 integration tests pass
# - test_health_check()
# - test_root_endpoint()
# - test_score_endpoint_missing_idempotency_key()
# - test_score_endpoint_valid_request()
# - test_score_endpoint_validation_error()
```

### Phase 4: Start Development Server (5 min)

```bash
# Via Docker (with auto-reload on code changes)
make docker-up
# App available at http://localhost:8000
# View logs: make docker-logs

# Or locally
make dev
# Same endpoints available at http://localhost:8000
```

**Available endpoints:**
- `GET  /`                    # Service metadata
- `GET  /v1/health`           # Health check
- `POST /v1/risk/score`       # Scoring endpoint (requires Idempotency-Key header)

### Phase 5: Validate Code Quality (5 min)

```bash
make lint      # Fix linting issues
make typecheck # Validate strict type checking
make test      # Full test suite
```

---

## Governance & Orchestration Compliance

### ✅ Enforced at Boundary

| Governance Rule | Implementation |
|---|---|
| **Idempotency on POST/PATCH** | `IdempotencyMiddleware` rejects `POST /v1/risk/score` without `Idempotency-Key` header (422 response) |
| **Structured logging for PCI audit trail** | structlog configured; all logs are JSON to stdout (never print/logging.info) |
| **Async Python throughout** | asyncpg + SQLAlchemy async; no synchronous drivers; no blocking I/O in handlers |
| **Pydantic v2 strict validation** | `RiskScoreRequest` validates at boundary; 422 on invalid payload |
| **Zero-downtime migrations** | Alembic `downgrade()` required on every migration; rollback tested |
| **Health endpoint for PRR** | `GET /v1/health` returns status + timestamp for observability/monitoring gate |
| **Database connection pooling** | PgBouncer-compatible pool config; `pool_size=20`, `max_overflow=0`, `pool_recycle=3600` |

### ✅ Cross-Agent Routing

**Architecture questions → @marcus**
- ADR-001 referenced (FastAPI choice)
- Database design can be reviewed

**Security questions → @priya**
- Future: JWT integration, Vault secrets, API key management

**Backend implementation → @sofia** (current owner)
- Complete: app layer, async, migrations, idempotency
- Next: Rule engine integration, Redis caching, Celery tasks

**QA/Testing → @aisha**
- Current: integration test template with Testcontainers
- Next: Contract tests (Pact), load test setup (Locust)

**Infrastructure → @darius**
- Kubernetes deployment manifests (k8s/)
- Terraform for AWS resources (terraform/)

---

## Directory Structure (Final)

```
app/
├── __init__.py
├── main.py                    # FastAPI app entry point + lifespan
├── config.py                  # Pydantic settings from env vars
├── core/
│   ├── logging.py             # structlog JSON setup
│   └── __init__.py
├── db/
│   ├── engine.py              # SQLAlchemy async engine + session
│   ├── models.py              # Base ORM models (lazy='raise' on relationships)
│   └── __init__.py
├── health/
│   ├── routes.py              # GET /v1/health
│   └── __init__.py
├── scoring/
│   ├── routes.py              # POST /v1/risk/score skeleton
│   ├── schemas.py             # Pydantic v2 models
│   └── __init__.py
└── middleware/
    ├── idempotency.py         # Idempotency-Key enforcement
    └── __init__.py

tests/
├── conftest.py                # Pytest fixtures (db_session, async_client, etc)
├── unit/
├── integration/
│   ├── test_health.py
│   └── test_scoring_endpoint.py
└── fixtures/

alembic/
├── env.py                     # Database migration environment
├── script.py.mako             # Migration template
├── alembic.ini                # Alembic config
├── versions/                  # Migration files (auto-generated)
└── __init__.py

.pre-commit-config.yaml        # Git hooks: Ruff, mypy, bandit
pyproject.toml                 # Build config, Ruff/mypy settings
pytest.ini                     # Pytest config
Makefile                       # Development tasks
requirements.txt               # Pinned dependencies
docker-compose.yml             # PostgreSQL + Redis
.env.example                   # Template environment file
```

---

## Critical Blockers & Assumptions

### Blocker 1: Redis Cluster for Idempotency (Sprint 2)

**Current:** IdempotencyMiddleware validates header presence only; no actual deduplication.

**Missing:** Redis integration for:
- Storing idempotency keys (24h TTL)
- Two-phase response caching (PROCESSING → COMPLETE)
- Conflict detection (different body, same key → 422)

**Unblocks:** Rule engine production integration, load testing at scale

**Sprint 2 Work:**
```python
# Placeholder in middleware/idempotency.py:
# TODO: Check Redis for existing key
# TODO: Store with PROCESSING status
# TODO: Cache response after completion
```

---

### Blocker 2: Rule Engine Integration (Sprint 2)

**Current:** `POST /v1/risk/score` returns mock score (0.35 MEDIUM).

**Missing:**
- Rule engine consumption from Kafka (ADR-008)
- BentoML model serving integration (ADR-004)
- Feature enrichment from Feast (part of ML pipeline)

**Unblocks:** Real risk scoring, production traffic

**skeleton Work:**
```python
# In scoring/routes.py:
# ❌ TODO: Call rule engine (RPC or Kafka)
# ❌ TODO: Integrate BentoML for model inference
# ❌ TODO: Enrich features from Feast
```

---

### Blocker 3: Audit Logging to Cassandra (Sprint 2–3)

**Current:** Structured logs to stdout only; no persistent audit trail.

**Missing:** Cassandra event log (ADR-002):
- Write-through for every transaction scored
- Immutable event log for compliance (PCI DSS Requirement 10)
- Retention policy (7 years for fraud investigations)

**Unblocks:** Compliance audits, post-incident investigation

---

### Blocker 4: Secrets Management (Sprint 2)

**Current:** Database credentials from environment variables (`.env`).

**Missing:** HashiCorp Vault integration (ISS-003):
- Dynamic credentials from Vault
- Automatic secret rotation (every 24h)
- App reload without restart

**Unblocks:** Production deployment, PCI DSS Requirement 2.2.4

---

### Assumption 1: PostgreSQL 16 + pgvector

The database engine is configured for PostgreSQL 16 with asyncpg driver.

**If using an older version:**
```bash
# Docker default (in docker-compose.yml) is postgres:16-alpine ✅
# If you need to downgrade:
# - Remove pgvector from requirements (not available in 14–15)
# - Remove vector columns from future schemas
```

---

### Assumption 2: Redis Available at Startup

The app does **not** yet require Redis to start (middleware is a no-op for caching).

**When integrating idempotency cache (Sprint 2):**
```python
# This will block startup if Redis unavailable:
# redis_client = redis.from_url(settings.redis_url)
# await redis_client.ping()
```

**Solution:** Use `startup` event to retry with exponential backoff.

---

### Assumption 3: Testcontainers Requires Docker

Integration tests spin up real PostgreSQL + Redis containers.

**Requirements:**
- Docker daemon running locally
- 10 min first-run overhead (downloading images)
- `-m integration` can be skipped for rapid unit test loops

**If Docker unavailable:**
```bash
# Run unit tests only (none currently, but template exists)
make test-unit
```

---

### Assumption 4: Alembic Database Connectivity

`alembic.env.py` reads from `app.config.settings`, requiring:
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=ras_dev

alembic upgrade head  # ✅ Will work
```

**If .env not loaded:**
```bash
# Manually source first
set -a
source .env
set +a
alembic upgrade head
```

---

## Development Workflow

### Daily Loop

```bash
# 1. Make code changes
vim app/scoring/routes.py

# 2. Run tests
make test

# 3. Lint + typecheck
make lint
make typecheck

# 4. If database schema changed:
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Pre-Commit (Git Hook)

```bash
git add .
git commit -m "Add feature"
# Automatically runs:
# - Ruff linter + formatter
# - mypy type check
# - Bandit security scan
# - Alembic status check

# If any check fails, fix and retry:
git commit --amend
```

### Before Merge

Per [governance.md](docs/governance/governance.md):

```bash
# 1. All CI checks passing (GitHub Actions)
✅ Unit tests
✅ Integration tests
✅ Linting (Ruff)
✅ Type checking (mypy strict)
✅ Security scan (Bandit)

# 2. Coverage ≥90% (line), ≥85% (branch)
make test-cov

# 3. Migration reversibility tested
alembic downgrade -1
alembic upgrade head

# 4. Domain owner approval (from orchestrator.md)
# For backend: @sofia
# For infrastructure: @darius
# For security: @priya
```

---

## Next Steps (Sprint 2)

### Priority 1: Rule Engine Integration

**Who:** @sofia (backend) + @marcus (architecture review)

```python
# scoring/engine.py
class RuleEngine:
    async def score(self, request: RiskScoreRequest) -> RiskScore:
        # 1. Fetch latest rules from Kafka (ADR-008)
        # 2. Evaluate transaction through rule tree
        # 3. Return score + tier + decision
```

### Priority 2: Redis Idempotency Cache

**Who:** @sofia (backend) + @darius (infrastructure)

```python
# middleware/idempotency.py
# Check Redis for existing response
# Store with TTL = 24h
# Conflict detection on body mismatch
```

### Priority 3: BentoML Integration

**Who:** @yuki (ML) + @sofia (backend)

```python
# scoring/ml_client.py
class BentoMLClient:
    async def predict(self, features: Dict) -> Decimal:
        # Call BentoML serving endpoint
        # Return fraud score [0.0, 1.0]
```

### Priority 4: Cassandra Audit Log

**Who:** @sofia (backend) + @marcus (architecture)

```python
# audit/cassandra.py
class AuditLog:
    async def write_score_event(self, request_id: UUID, event: ScoringEvent):
        # Write immutable event to Cassandra
        # PCI DSS Requirement 10 compliance
```

---

## Running and Debugging

### Start Development Environment

```bash
# Terminal 1: Start services
docker-compose up -d

# Terminal 2: Run dev server
make dev

# Terminal 3: Run tests
make test

# Terminal 4: Monitor logs
docker-compose logs -f postgres redis
```

### Common Commands

```bash
# Health check
curl http://localhost:8000/v1/health

# Score a transaction (requires Idempotency-Key)
curl -X POST http://localhost:8000/v1/risk/score \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "transaction_id": "txn_123",
    "customer_id": "cust_456",
    "amount_cents": 10000,
    "merchant_id": "merch_789",
    "currency": "USD"
  }'

# View logs
docker-compose logs postgres -f

# Verify database
docker-compose exec postgres psql -U postgres -d ras_dev -c "\dt"

# Drop and recreate database (careful in dev only!)
docker-compose exec postgres dropdb -U postgres ras_dev
docker-compose exec postgres createdb -U postgres ras_dev
alembic upgrade head
```

### Database Troubleshooting

```bash
# Check connection
python -c "from app.db.engine import engine; \
from sqlalchemy import select, func; \
import asyncio; \
asyncio.run(engine.connect())"

# View current migrations
alembic current

# Show migration history
alembic history --verbose

# Rollback 1 migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade 12e1b3f12345
```

### Testing Troubleshooting

```bash
# If Testcontainers fail (Docker not running):
# Error: testcontainers.core.exceptions.DockerException

# Solution:
docker-compose up -d  # Start services first

# Run with verbose pytest output
make test-cov  # Shows which tests run

# Debug specific test
pytest -xvs tests/integration/test_health.py::test_health_check
```

---

## Governance Checkpoints

### Pre-Merge Checklist

- [ ] All tests pass (unit + integration)
- [ ] Coverage ≥90% line, ≥85% branch
- [ ] mypy strict mode: zero errors
- [ ] Ruff lint: zero errors
- [ ] Bandit security: zero CRITICAL/HIGH
- [ ] Database migration: rollback tested
- [ ] Pre-commit hooks pass
- [ ] Async code: no blocking I/O
- [ ] Pydantic validation: at boundary only
- [ ] N+1 queries: checked with EXPLAIN ANALYZE

### Pre-Production Checklist (@aisha PRR Gate)

- [ ] Load test P95 <100ms @2x peak
- [ ] Rollback plan documented + tested
- [ ] Health endpoint responding
- [ ] Audit logging configured
- [ ] PgBouncer pool not saturated
- [ ] Structured logs flowing to Loki
- [ ] Prometheus metrics defined
- [ ] Runbook for on-call: "Scoring API down"
- [ ] Secrets rotated and verified
- [ ] External pentest (PCI req): passed or waived

---

## References

- [CLAUDE.md](../CLAUDE.md) — Agent system & tech stack
- [orchestrator.md](../.claude/orchestrator.md) — Routing and collaboration
- [governance.md](../docs/governance/governance.md) — Engineering enforcement rules
- [DOCKER_SETUP.md](../DOCKER_SETUP.md) — Docker setup & deployment guide
- [ADR-001: FastAPI](../docs/architecture/adr/ADR-001-fastapi-framework.md)
- [ADR-002: Cassandra](../docs/architecture/adr/ADR-002-cassandra-event-log.md)
- [ADR-006: Redis Velocity](../docs/architecture/adr/ADR-006-redis-velocity-counters.md)

---

**Last Updated:** March 25, 2026  
**Owner:** @sofia (Backend) + @marcus (Architecture)  
**Sprint:** 1  
**Status:** ✅ Ready for implementation
