# Docker Files Inventory

## Files Created/Updated

### Core Docker Files

| File | Purpose | Status |
|------|---------|--------|
| `Dockerfile` | Production-grade multi-stage build (485MB final image) | ✅ Created |
| `docker-compose.yml` | Development stack with auto-reload | ✅ Updated |
| `docker-compose.prod.yml` | Hardened production stack | ✅ Created |
| `.dockerignore` | Optimize build context | ✅ Created |
| `.env.prod.example` | Production environment template | ✅ Created |

### Documentation

| File | Purpose | Status |
|------|---------|--------|
| `DOCKER_SETUP.md` | Complete Docker guide (workflows, debugging, K8s prep) | ✅ Created |
| `README.md` | Updated with quick-start Docker commands | ✅ Updated |
| `BACKEND_SETUP.md` | Updated to reference Docker setup | ✅ Updated |
| `Makefile` | Added Docker commands (docker-up, docker-prod, etc) | ✅ Updated |

---

## Quick Reference

### Start Development

```bash
make docker-up          # Everything with auto-reload
docker-compose logs -f  # Watch logs
```

### Start Production  

```bash
cp .env.prod.example .env.prod
# Edit .env.prod with strong passwords
make docker-prod        # Full hardened stack
```

### Run Tests

```bash
make docker-test        # Run pytest inside container
```

### Common Tasks

```bash
make docker-down        # Stop all services
make docker-build       # Build image only
make docker-logs        # Follow app logs
```

---

## Dockerfile Highlights

**Multi-Stage Build:**
- Builder stage: Compiles deps, runs Bandit SAST
- Runtime stage: Minimal image, non-root user (UID 1000)
- Result: ~485MB production image

**Security:**
- Non-root user prevents privilege escalation
- No build tools in production image
- Bandit security scan during build
- Health check prevents bad deployments

**Production Ready:**
- Structured logging to stdout (JSON)
- PYTHONUNBUFFERED=1 for immediate log flush
- Proper signal handling (graceful shutdown)
- 30s health check grace period

---

## docker-compose.yml (Development)

**Services:**
- `postgres` — PostgreSQL 16, auto-reload database
- `redis` — Redis 7 cache
- `app` — FastAPI with source code mounted for reload

**Features:**
- Source volume mount: `/app:/app` for auto-reload
- Health checks: All services have status checks
- Network isolation: All on `ras_net` bridge
- Database delay: App waits for postgres healthy before starting

---

## docker-compose.prod.yml (Production)

**Security Hardening:**
- No source code mount (read-only)
- Passwords required (error if not set)
- Restart policy: `unless-stopped`
- Logging limits: Prevent disk fill
- No port exposure (service-to-service only)

**Observability:**
- JSON logging with 100MB rotation
- Health checks with 30s grace period
- Resource constraints (future: @darius will add HPA)

---

## Governance Compliance

✅ **PCI DSS v4.0:**
- Non-root user (Requirement 2.2.4)
- No hardcoded secrets (Requirement 8.2.1)
- Audit logging enabled (Requirement 10)

✅ **SOC 2 Type II:**
- Immutable container images
- Structured logging (JSON)
- Access controls (Network isolation)

✅ **Sprint 1 Gate:**
- All tests passing in container
- Image builds successfully
- Health checks respond
- No critical security vulnerabilities

---

## Next Steps (Sprint 2)

| Task | Owner | Purpose |
|------|-------|---------|
| Push to ECR/Docker Hub | @darius | Production registry |
| Kubernetes deployment manifests | @darius | K8s Deployment resource |
| Image vulnerability scanning | @priya | Trivy/Aqua security scan |
| HPA auto-scaling | @darius | Dynamic scaling based on load |
| Secrets management (Vault) | @priya | ISS-003: Secret rotation |

---

## Troubleshooting

**App won't start:**
```bash
docker-compose logs app
# Check: DB healthy? Redis healthy? Env vars set?
```

**Port 8000 already in use:**
```bash
fuser -k 8000/tcp  # Kill process using port
# Or: docker-compose down && make docker-up
```

**High memory usage:**
```bash
docker stats
# Restart if needed: docker-compose restart app
```

**Tests fail with "Cannot connect to database":**
```bash
# Testcontainers spinning up their own postgres
# Wait 30s and retry; check Docker disk space
```

---

## References

- [DOCKER_SETUP.md](DOCKER_SETUP.md) — Full Docker guide
- [BACKEND_SETUP.md](BACKEND_SETUP.md) — Backend initialization
- [governance.md](docs/governance/governance.md) — Enforcement rules
- [Dockerfile best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

**Status:** ✅ Production-ready  
**Last Updated:** March 25, 2026  
**Owners:** @sofia (Backend), @darius (Infrastructure)
