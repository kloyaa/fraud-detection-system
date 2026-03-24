# Docker Setup Guide — RAS Backend

> Risk Assessment System (RAS) v1.0.0  
> Production-Grade Docker Configuration  
> **Last Updated:** March 25, 2026

---

## Quick Start (5 Minutes)

### Development Mode (Auto-Reload)

```bash
# Start all services with source code mounted
docker-compose up -d

# Watch logs
docker-compose logs -f app

# Stop services
docker-compose down
```

Access app at `http://localhost:8000`

### Production Mode (Docker Only)

```bash
# Set credentials
cp .env.prod.example .env.prod
vim .env.prod  # Fill in POSTGRES_PASSWORD, REDIS_PASSWORD

# Start stack
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Health check
docker exec ras_app_prod curl -s http://localhost:8000/v1/health | jq '.'
```

---

## Why Docker?

The RAS backend uses Docker for:

✅ **Consistency** — Exactly the same environment from dev → staging → production  
✅ **Isolation** — No system package conflicts or Python version issues  
✅ **Compliance** — Non-root user, minimal image, security scanning (Bandit)  
✅ **Orchestration** — Ready for Kubernetes (K8s) deployment  
✅ **Reproducibility** — All dependencies pinned, deterministic builds  

---

## Architecture

### Multi-Stage Build (`Dockerfile`)

The Dockerfile uses two stages to minimize production image size:

| Stage | Purpose | Artifacts |
|-------|---------|-----------|
| **Builder** (1) | Compile Python dependencies, run SAST security scan | Python wheels |
| **Runtime** (2) | Minimal image with only runtime deps, non-root user | ~500MB final image |

**Benefits:**
- Production image excludes build tools (gcc, apt build-essentials)
- No source code or development files in production
- Bandit security scan catches SAST issues early
- Non-root user prevents privilege escalation

### Docker Compose Stacks

| File | Purpose | Environment |
|------|---------|-------------|
| `docker-compose.yml` | Full stack with app source reload | **Development** |
| `docker-compose.prod.yml` | Hardened production-ready stack | **Production** |

---

## Development Workflow

### Start Full Stack (with Auto-Reload)

```bash
docker-compose up -d

# Verify services started
docker-compose ps

# Expected output:
# NAME              COMMAND                  SERVICE     STATUS      PORTS
# ras_postgres_dev  postgres                 postgres    healthy     0.0.0.0:5432->5432/tcp
# ras_redis_dev     redis-server             redis       healthy     0.0.0.0:6379->6379/tcp
# ras_app_dev       uvicorn app.main:app...  app         healthy     0.0.0.0:8000->8000/tcp
```

### Test the Application

```bash
# Health check
curl http://localhost:8000/v1/health

# Score a transaction
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
```

### View Logs

```bash
# All services
docker-compose logs

# Follow app logs only
docker-compose logs -f app

# Last 100 lines of postgres logs
docker-compose logs --tail=100 postgres
```

### Run Migrations

```bash
# Inside running app container
docker-compose exec app alembic upgrade head

# Or from host (app auto-runs on startup)
# Migrations applied automatically via Alembic in app.main.py lifespan
```

### Run Tests

```bash
# Execute test suite inside app container
docker-compose exec app pytest -xvs

# Run with coverage
docker-compose exec app pytest --cov=app --cov-report=html

# Run integration tests only (Testcontainers will spin up their own containers)
docker-compose exec app pytest -xvs -m integration
```

### Code Changes & Reload

```bash
# Edit any .py file in app/
vim app/scoring/routes.py

# Server automatically reloads thanks to volume mount + uvicorn --reload
# Check logs to verify:
docker-compose logs -f app

# Expected output:
# ras_app_dev | INFO:     Uvicorn running on http://0.0.0.0:8000
# ras_app_dev | INFO:     Application startup complete
```

### Restart Individual Services

```bash
# Restart only the app (keep DB, Redis)
docker-compose restart app

# Rebuild and restart app after dependency change
docker-compose up --build app -d

# Recreate all (deletes volumes!)
docker-compose down -v
docker-compose up -d
```

### Access Database Shell

```bash
# Open psql inside postgres container
docker-compose exec postgres psql -U postgres -d ras_dev

# Common commands:
\dt          # List all tables
\d tasks     # Describe table schema
SELECT * FROM table_name;

# Exit
\q
```

### Access Redis CLI

```bash
# Open redis-cli inside redis container
docker-compose exec redis redis-cli

# Common commands:
PING                    # Test connection (reply: PONG)
KEYS *                  # List all keys
GET <key>               # Fetch key value
MONITOR                 # Watch all commands
SHUTDOWN                # Graceful shutdown
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] All tests passing (`docker-compose exec app pytest`)
- [ ] Code linted (`docker-compose exec app ruff check .`)
- [ ] Types validated (`docker-compose exec app mypy app`)
- [ ] Security scan clean (`docker-compose exec app bandit -r app`)
- [ ] Database migrations tested (`alembic upgrade head && alembic downgrade -1`)
- [ ] `.env.prod` configured with strong passwords (20+ chars)
- [ ] Docker image built and scanned for vulnerabilities
- [ ] Load test passing (P95 <100ms)

### Build Production Image

```bash
# Manual build
docker build -t ras:1.0.0 --target runtime .

# Tag for registry (AWS ECR example)
docker tag ras:1.0.0 123456789.dkr.ecr.us-east-1.amazonaws.com/ras:1.0.0

# Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/ras:1.0.0

# Verify image
docker images ras:1.0.0
# REPOSITORY  TAG    IMAGE ID      CREATED      SIZE
# ras         1.0.0  abcd1234567   2 min ago    485MB
```

### Run Production Stack (Docker Only)

```bash
# 1. Set up production environment
cp .env.prod.example .env.prod

# 2. Edit with production credentials
vim .env.prod

# Required values (use AWS Secrets Manager or HashiCorp Vault in production):
# POSTGRES_PASSWORD=<strong_password>
# REDIS_PASSWORD=<strong_password>

# 3. Start stack
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 4. Verify health
docker ps
docker-compose -f docker-compose.prod.yml logs app

# 5. Run database migrations
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

### Verify Production Deployment

```bash
# Health check (inside container)
docker exec ras_app_prod curl http://localhost:8000/v1/health

# Expected output:
# {
#   "status": "healthy",
#   "timestamp": "2026-03-25T14:30:00+00:00",
#   "version": "1.0.0"
# }

# Check logs for errors
docker-compose -f docker-compose.prod.yml logs app

# Monitor resource usage
docker stats ras_app_prod
```

---

## Security Best Practices

### Built Into Dockerfile

✅ **Multi-stage build** — Removes build tools from final image  
✅ **Non-root user** — App runs as `appuser` (UID 1000), not root  
✅ **Minimal base image** — `python:3.12-slim` (~150MB vs 1GB full image)  
✅ **Security scanning** — Bandit SAST runs during build  
✅ **No hardcoded secrets** — All config from environment variables  
✅ **Read-only code** — Application code copied, not mounted in production  

### Production Stack (docker-compose.prod.yml)

✅ **Health checks** — All services have 30s+ grace period before restart  
✅ **Restart policy** — `unless-stopped` prevents restart loops  
✅ **Logging limits** — Max 100MB per file, 10 files rotated (prevents disk fill)  
✅ **Password enforcement** — Redis/Postgres require strong passwords  
✅ **Network isolation** — Services on internal `ras_net` bridge only  
✅ **Volume permissions** — Database/Redis data owned by system users  

### Before Production Deployment

```bash
# 1. Scan image for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image ras:1.0.0

# 2. Check for high-severity CVEs
# If found, update base image + dependencies, rebuild

# 3. Sign image (optional, for Kubernetes)
cosign sign --key cosign.key ras:1.0.0

# 4. Use secrets management (not .env file in production)
# Option A: AWS Secrets Manager
# Option B: HashiCorp Vault
# Option C: Kubernetes Secrets (if on K8s)
```

---

## Debugging

### App Container Won't Start

```bash
# Check logs
docker-compose logs app

# Common issues:
#
# 1. "Cannot connect to database" — postgres not healthy yet
#    Solution: Wait 30s and retry
#
# 2. "Port 8000 already in use" — another process on port
#    Solution: docker-compose down; or fuser -k 8000/tcp
#
# 3. "PYTHONPATH not set" — import errors
#    Solution: Verify WORKDIR in Dockerfile is correct

# Inspect container state
docker-compose inspect app
docker-compose ps --all

# Run container with debug shell
docker-compose run --entrypoint /bin/bash app
# Inside container:
# $ python -c "import app; print(app.__version__)"
# $ alembic --version
# $ exit
```

### Database Connection Errors

```bash
# 1. Verify postgres is healthy
docker-compose ps postgres

# 2. Check connection from app
docker-compose exec app python -c \
  "from app.db.engine import engine; \
   import asyncio; \
   asyncio.run(engine.connect())"

# 3. Manually connect to postgres
docker-compose exec postgres psql -U postgres -c "SELECT 1"

# 4. Check environment variables in app
docker-compose exec app printenv | grep POSTGRES
```

### Redis Connection Errors

```bash
# 1. Verify redis is healthy
docker-compose ps redis

# 2. Test connection
docker-compose exec redis redis-cli ping
# Expected: PONG

# 3. Check keys exist
docker-compose exec redis redis-cli KEYS "*"

# 4. Flush all (dev only!)
docker-compose exec redis redis-cli FLUSHALL
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Expected (development):
# CONTAINER    CPU %  MEM USAGE / LIMIT   MEM %
# ras_app_dev  0.5%   120MiB / 8GiB       1%
# ras_postgres_dev 2% 150MiB / 8GiB      1%
# ras_redis_dev    1% 5MiB / 8GiB        0%

# If memory high:
# 1. Check for memory leaks
# 2. Reduce connection pool size
# 3. Restart container

# If CPU high:
# 1. Profile app: docker-compose exec app python -m cProfile
# 2. Check database slow queries: EXPLAIN ANALYZE
# 3. Check redis memory: redis-cli INFO memory
```

---

## Common Commands

### Build & Run

```bash
# Build image (development only)
docker build -t ras:dev .

# Build with no cache (forces rebuild)
docker build --no-cache -t ras:1.0.0 .

# Run container manually (without compose)
docker run -d \
  -e POSTGRES_HOST=postgres \
  -e POSTGRES_DB=ras_dev \
  -p 8000:8000 \
  --name ras_app \
  ras:dev

# Run with mounted source (for development)
docker run -d \
  -v $(pwd)/app:/app/app \
  -p 8000:8000 \
  ras:dev
```

### Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (data loss!)
docker-compose down -v

# Remove all stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove everything (containers, images, volumes, networks)
docker system prune -a
```

### Inspect & Logs

```bash
# Show container details
docker-compose inspect app | jq '.'

# Follow logs in real-time
docker-compose logs -f --tail=50 app

# Show logs from specific time
docker-compose logs --since 5m app

# Export logs to file
docker-compose logs app > logs.txt
```

### Database Backup & Restore

```bash
# Backup database
docker-compose exec postgres pg_dump -U postgres ras_dev > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres ras_dev < backup.sql

# Backup volume directly
docker run --rm -v ras_postgres_data:/data \
  -v $(pwd):/backup \
  busybox tar czf /backup/postgres_data.tar.gz -C /data .
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/docker-build.yml
name: Build Docker Image

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: docker build -t ras:${{ github.sha }} .

      - name: Scan with Trivy
        uses: aquasec/trivy-action@master
        with:
          image-ref: ras:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif

      - name: Upload SARIF report
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: trivy-results.sarif

      - name: Run tests in Docker
        run: docker run --rm ras:${{ github.sha }} pytest -xvs

      - name: Push to ECR (if main)
        if: github.ref == 'refs/heads/main'
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR
          docker tag ras:${{ github.sha }} $ECR/ras:latest
          docker push $ECR/ras:latest
```

---

## Kubernetes Deployment (Future)

When deploying to Kubernetes, use:

1. **Docker image** built above (pushed to ECR/Docker Hub)
2. **ConfigMap** for non-secret settings (API_PORT, LOG_LEVEL)
3. **Secret** for credentials (POSTGRES_PASSWORD, REDIS_PASSWORD)
4. **Deployment** with resource requests/limits
5. **Service** for network exposure
6. **HorizontalPodAutoscaler** for scaling (future: @darius owns this)

Example (Sprint 2):

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ras-api
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: app
          image: ras:1.0.0
          ports:
            - containerPort: 8000
          env:
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: ras-secrets
                  key: db-password
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /v1/health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
```

---

## Environment Variables Reference

### Development (docker-compose.yml)

| Variable | Value | Purpose |
|----------|-------|---------|
| `ENVIRONMENT` | `development` | Enables debug mode, verbose logging |
| `DEBUG` | `True` | FastAPI debug mode |
| `POSTGRES_HOST` | `postgres` | Container hostname (DNS resolution) |
| `POSTGRES_DB` | `ras_dev` | Database name |
| `LOG_LEVEL` | `DEBUG` | Verbose logging |

### Production (docker-compose.prod.yml)

| Variable | Value | Purpose |
|----------|-------|---------|
| `ENVIRONMENT` | `production` | Disables debug |
| `DEBUG` | `False` | FastAPI production mode |
| `LOG_LEVEL` | `INFO` | Business events only |
| `POSTGRES_PASSWORD` | `${POSTGRES_PASSWORD}` | **Required** — set in .env.prod |
| `REDIS_PASSWORD` | `${REDIS_PASSWORD}` | **Required** — set in .env.prod |

---

## Governance Compliance

✅ **PCI DSS Requirements:**
- Non-root user (prevents privilege escalation)
- Secrets not in code (environment variables)
- Logging enabled (JSON to stdout)
- Health checks (detect issues early)

✅ **SOC 2 Type II:**
- Immutable container images
- Audit trails (app logs structured)
- Access controls (network isolation)

✅ **Compliance Gates:**
- Image scanning (Trivy/Bandit) before deploy
- Testing in container (pytest runs inside)
- Health checks prevent bad deployments
- Secrets management plan (Vault in Sprint 2)

---

## Troubleshooting Checklist

| Issue | Check | Solution |
|-------|-------|----------|
| App won't start | Logs: `docker-compose logs app` | Usually: wait for DB to be healthy |
| Can't connect to DB | Postgres logs: `docker-compose logs postgres` | Check POSTGRES_* environment variables |
| Tests failing | Run inside container: `docker-compose exec app pytest -xvs` | Check database state |
| High memory usage | `docker stats` | Restart container, check for leaks |
| Image too large | `docker images` | Use multi-stage build (already done) |
| Permissions denied | Check file ownership: `ls -la` | Use `docker-compose exec` not `sudo` |

---

## References

- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [security/hardening_standards.md](docs/security/hardening_standards.md) — Full security hardening guide
- [BACKEND_SETUP.md](BACKEND_SETUP.md) — Backend setup guide
- [CLAUDE.md](CLAUDE.md) — Agent system & tech stack

---

**Owner:** @sofia (Backend) + @darius (Infrastructure)  
**Status:** ✅ Production ready  
**Last Updated:** March 25, 2026
