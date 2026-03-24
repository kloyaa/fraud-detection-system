# Risk Assessment System (RAS)

Production-grade fraud detection and risk scoring platform for transaction processing and customer risk evaluation.

**Version:** 1.0.0  
**Language:** Python 3.12+ | TypeScript/Next.js  
**SLA:** 99.99% uptime | P95 latency <100ms  
**Compliance:** PCI DSS v4.0 | SOC 2 Type II | GDPR | CCPA | ISO 27001

---

## Quick Start

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- Node.js 18+
- PostgreSQL 16, Redis 7 (or Docker services)

### Setup

```bash
# Clone and enter repo
git clone <repo_url>
cd fraud-detection-system

# Python environment
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate (Windows)
pip install -r requirements.txt

# Database setup
alembic upgrade head

# Start services (development)
docker-compose up -d
make dev  # or: python -m uvicorn app.main:app --reload
```

---

## Project Structure

```
fraud-detection-system/
├── CLAUDE.md                                     ← Agent system & project intelligence
├── Technical Documentation.md                    ← Getting started guide
├── .claude/
│   ├── agents/                                   ← 10 domain agents + 2 utility agents
│   ├── orchestrator.md                           ← Multi-agent routing & collaboration
│   └── governance/
│       └── governance.md                         ← Engineering enforcement rules
├── docs/
│   ├── architecture/                             ← System design & ADRs (8 ADRs)
│   ├── compliance/                               ← PCI DSS, GDPR, SOC 2
│   ├── security/                                 ← Encryption, threat model, RBAC
│   ├── ml/                                       ← Model pipeline, governance
│   └── quality/                                  ← PRR checklist, test strategy
├── app/                                          ← FastAPI application
│   ├── main.py                                   ← Entry point
│   ├── scoring/                                  ← Scoring service
│   ├── rules/                                    ← Rule engine
│   └── models/                                   ← Data models (Pydantic)
├── ml/                                           ← ML workloads
│   ├── training/                                 ← XGBoost/LightGBM training
│   ├── serving/                                  ← BentoML serving
│   └── features/                                 ← Feast feature store
├── tests/                                        ← Test suites
│   ├── unit/                                     ← Unit tests (pytest)
│   ├── integration/                              ← Integration tests (Testcontainers)
│   ├── contract/                                 ← Pact contract tests
│   ├── load/                                     ← Locust load tests
│   └── security/                                 ← Security test suite
├── k8s/                                          ← Kubernetes manifests
├── terraform/                                    ← Infrastructure as Code
└── requirements.txt                              ← Python dependencies
```

---

## Key Documentation

**Start Here:**
- [Technical Documentation](Technical%20Documentation.md) — Project overview & onboarding
- [CLAUDE.md](CLAUDE.md) — Agent system, team roster, ADRs, technology stack

**Architecture:**
- [System Overview](docs/architecture/system_overview.md)
- [Architectural Decision Records](docs/architecture/adr/)
- [Capacity Plan](docs/architecture/capacity_plan.md)
- [Kafka Topics](docs/architecture/kafka_topics.md)

**Engineering:**
- [Governance Rules](docs/governance/governance.md) — **Non-negotiable enforcement gates**
- [Agent Orchestration](/.claude/orchestrator.md) — Routing, collaboration, authority
- [PRR Checklist](docs/quality/prr_checklist.md) — Production readiness review

**Security & Compliance:**
- [Encryption Specification](docs/security/encryption_spec.md)
- [RBAC Matrix](docs/security/rbac_matrix.md)
- [Threat Model](docs/security/threat_model.md)
- [PCI DSS Controls](docs/compliance/pci_dss_controls.md)
- [GDPR DPIA](docs/compliance/gdpr_dpia.md)

**ML & Models:**
- [Model Card](docs/security/model_card.md)
- [Pipeline Architecture](docs/ml/pipeline_architecture.md)

---

## Team & Agents

The RAS team uses a multi-agent system for decision-making and code review.

| Role | Agent | Domain |
|------|-------|--------|
| Chief Risk Architect | @marcus | System design, architecture, ADRs |
| Principal Security Engineer | @priya | Security, encryption, threat modeling |
| Lead ML / Risk Scientist | @yuki | Machine learning, model governance |
| Staff SRE / Platform Engineer | @darius | Infrastructure, SRE, chaos, observability |
| Senior Backend Engineer | @sofia | FastAPI, SQLAlchemy, async, migrations |
| Head of Risk & Compliance | @james | GDPR, PCI DSS, SOC 2, AML/KYC, FCRA |
| Principal QA / Test Engineer | @aisha | Quality gates, PRR, test strategy, load testing |
| Senior Frontend Engineer | @elena | Next.js, React, TypeScript, accessibility |

**Utility Agents:**
- @optimizer — Code review & agent optimization
- @doc-integrity — Documentation reference validation

For invocation patterns and collaboration workflows, see [Agent Orchestration](/.claude/orchestrator.md).

---

## Development Workflow

### Pre-Commit

```bash
make lint        # ruff, eslint
make type-check  # mypy, tsc
make test        # pytest (unit + integration)
```

### Before Merge (Governance Gates)

✅ All CI checks passing  
✅ Line coverage ≥90%, branch coverage ≥85%  
✅ Zero CRITICAL/HIGH security findings  
✅ Domain owner approval (see [Governance](docs/governance/governance.md))

### Before Deployment (PRR Gates)

✅ Production Readiness Review completed with GO decision  
✅ Load test validated (P95 <100ms @2x peak, error <0.1%)  
✅ Rollback tested with evidence  
✅ All 6 PRR sections approved

See [Governance Rules](docs/governance/governance.md) and [Production Readiness Review](docs/quality/prr_checklist.md).

---

## Running Tests

```bash
# Unit tests
pytest tests/unit/ -v --cov=app --cov-report=html

# Integration tests (requires Docker services)
pytest tests/integration/ -v --testcontainers

# Contract tests (Pact)
pytest tests/contract/ -v

# Load tests (Locust)
locust -f tests/load/locustfile.py --host http://localhost:8000

# Security tests
pytest tests/security/ -v  # OWASP ZAP, injection, auth bypass
```

---

## Deployment

### Development
```bash
make dev  # uvicorn with reload
```

### Staging
```bash
docker build -t ras:latest .
docker-compose -f docker-compose.staging.yml up -d
```

### Production
```bash
# All governance gates must pass (see docs/governance/governance.md)
kubectl apply -f k8s/production/
argocd app sync ras-prod
```

---

## Key Technologies

**Application:** FastAPI, Pydantic, SQLAlchemy, Alembic  
**Data:** PostgreSQL, Cassandra, Redis, Neo4j, Elasticsearch  
**ML:** XGBoost, LightGBM, Feast, BentoML, MLflow  
**Infrastructure:** Kubernetes (EKS), Terraform, Helm, ArgoCD  
**Observability:** Prometheus, Grafana, Jaeger, Loki  
**Security:** AWS KMS, HashiCorp Vault, Istio mTLS  
**Testing:** pytest, Testcontainers, Pact, Locust, OWASP ZAP

---

## Open Issues

| Issue | Owner | Priority | Target |
|-------|-------|----------|--------|
| ISS-001: ML model cold-start >300ms | @yuki | P1 | Reduce to <30ms P95 |
| ISS-002: PgBouncer pool exhaustion | @sofia | P1 | Stabilize <80% utilization |
| ISS-003: Vault secret rotation wiring | @priya | P2 | Implement dynamic reload |
| ISS-004: Neo4j traversal timeout | @marcus | P2 | Refactor or cache |
| ISS-005: Cassandra runbook missing | @darius | P2 | Document + test |

---

## Contributing

1. **Read governance rules** — [docs/governance/governance.md](docs/governance/governance.md)
2. **Review agent responsibilities** — [CLAUDE.md](CLAUDE.md)
3. **Create feature branch** — `git checkout -b feature/your-feature`
4. **Pass pre-commit checks** — `make lint test type-check`
5. **Submit PR** — Request review from domain owner (see governance matrix)
6. **Merge gates** — All CI + domain approvals required
7. **Deploy** — PRR gates + orchestration authority required

---

## Support & Escalation

- **Questions?** Check [Technical Documentation](Technical%20Documentation.md)
- **Governance conflict?** Escalate to @aisha (QA authority) or VP Engineering
- **Security issue?** Contact @priya immediately
- **Compliance question?** Contact @james
- **Architecture decision?** Consult @marcus or see [ADR Index](docs/architecture/adr/)

---

## License

Proprietary — Risk Assessment System (internal use only)

---

**Last Updated:** March 25, 2026  
**Maintainers:** @marcus, @aisha, @priya, @darius (core team)
