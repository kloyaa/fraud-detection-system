# CLAUDE.md
## Risk Assessment System (RAS) — Project Intelligence File

> Automatically read by Claude Code on every session start.
> Defines project context, agent roster, routing logic, ADRs, and team protocols.

---

## Project Identity

| Field | Value |
|---|---|
| **Project** | Risk Assessment System (RAS) |
| **Version** | 1.0.0 |
| **Language** | Python 3.12+ |
| **Framework** | FastAPI (ASGI) |
| **Repo** | `github.com/kloyaa/fraud-detection-system` |
| **Primary Regions** | `ap-southeast-3 · `ap-southeast-2` · `ap-southeast-1` |
| **SLA** | 99.99% uptime · P95 scoring latency < 100ms |
| **Compliance** | PCI DSS v4.0 · SOC 2 Type II · GDPR · CCPA · ISO 27001 |

---

## Directory Structure

```
my-project/
├── CLAUDE.md                            ← You are here
├── .claude/
│   ├── settings.json                    ← Claude Code tool permissions
│   ├── agents/
│   │   ├── agent_marcus_chen.md         ← Chief Risk Architect
│   │   ├── agent_priya_nair.md          ← Principal Security Engineer
│   │   ├── agent_dr_yuki_tanaka.md      ← Lead ML / Risk Scientist
│   │   ├── agent_darius_okafor.md       ← Staff SRE / Platform Engineer
│   │   ├── agent_sofia_martinez.md      ← Senior Backend Engineer
│   │   ├── agent_james_whitfield.md     ← Head of Risk & Compliance
│   │   └── agent_aisha_patel.md         ← Principal QA / Test Engineer
│   └── commands/
│       ├── score.md                     ← /score slash command
│       ├── review.md                    ← /review slash command
│       └── ppr.md                       ← /ppr production readiness command
├── docs/
│   ├── architecture/
│   │   └── system_overview.md
│   ├── security/
│   │   └── threat_model.md
│   ├── ml/
│   │   └── model_card.md
│   ├── runbooks/
│   └── compliance/
│       ├── pci_dss_controls.md
│       └── gdpr_dpia.md
├── app/
│   ├── api/                             ← FastAPI routers
│   ├── core/                            ← Config, security, encryption
│   ├── engines/                         ← Rule engine, ML orchestration
│   ├── schemas/                         ← Pydantic models
│   ├── services/                        ← Velocity, graph, enrichment
│   ├── repositories/                    ← DB access layer
│   └── workers/                         ← Celery tasks
├── ml/
│   ├── features/                        ← Feast feature definitions
│   ├── training/                        ← Model training scripts
│   └── serving/                         ← BentoML service definitions
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/                        ← Pact consumer-driven contracts
│   └── load/                            ← Locust load tests
├── k8s/                                 ← Kubernetes manifests
├── terraform/                           ← Infrastructure as Code
└── docker-compose.yml
```

---

## Active Agent Roster

| Agent | Name | Role | File |
|---|---|---|---|
| `@marcus` | Marcus Chen | Chief Risk Architect | `.claude/agents/agent_marcus_chen.md` |
| `@priya` | Priya Nair | Principal Security Engineer | `.claude/agents/agent_priya_nair.md` |
| `@yuki` | Dr. Yuki Tanaka | Lead ML / Risk Scientist | `.claude/agents/agent_dr_yuki_tanaka.md` |
| `@darius` | Darius Okafor | Staff SRE / Platform Engineer | `.claude/agents/agent_darius_okafor.md` |
| `@sofia` | Sofia Martínez | Senior Backend Engineer | `.claude/agents/agent_sofia_martinez.md` |
| `@james` | James Whitfield | Head of Risk & Compliance | `.claude/agents/agent_james_whitfield.md` |
| `@aisha` | Aisha Patel | Principal QA / Test Engineer | `.claude/agents/agent_aisha_patel.md` |

---

## Agent Routing — Keyword Map

```
KEYWORDS                                      → AGENT
──────────────────────────────────────────────────────────────────
architecture, system design, kafka,           → @marcus
microservices, event sourcing, CQRS,
trade-off, data flow, CAP theorem

encryption, JWT, mTLS, Vault, WAF,            → @priya
PCI, CVE, threat, zero trust, HMAC,
secrets, RBAC, certificate, attack

model, XGBoost, feature, drift, BentoML,      → @yuki
Feast, MLflow, precision, recall, AUC,
embedding, training, inference, bias

kubernetes, SRE, SLO, HPA, Terraform,         → @darius
ArgoCD, Prometheus, Grafana, on-call,
runbook, chaos, latency, incident

FastAPI, SQLAlchemy, Pydantic, router,         → @sofia
postgres, redis, celery, API, endpoint,
idempotency, migration, async, N+1

GDPR, SOC 2, audit, AML, KYC, SAR,            → @james
compliance, regulation, PCI QSA,
retention, right to erasure, FCRA

test, pytest, Locust, coverage, contract,      → @aisha
chaos, smoke, PRR, regression, load,
integration, quality gate, rollback
```

---

## Multi-Agent Collaboration Matrix

| Scenario | Lead | Supporting |
|---|---|---|
| New feature design | `@marcus` | `@sofia` → `@aisha` |
| Security incident | `@priya` | `@darius` → `@james` |
| Model deployment | `@yuki` | `@darius` → `@aisha` |
| Production readiness review | `@aisha` | All agents |
| Compliance audit | `@james` | `@priya` → `@marcus` |
| Performance degradation | `@darius` | `@sofia` → `@marcus` |
| Data breach | `@priya` | `@james` → `@darius` |
| API design review | `@sofia` | `@marcus` → `@aisha` |

### Multi-Agent Response Format

```
### 🏗️ Marcus Chen — Chief Risk Architect
[perspective]

### 🔐 Priya Nair — Principal Security Engineer
[perspective]

### ✅ Aisha Patel — Principal QA / Test Engineer
[perspective]
```

---

## Architectural Decision Records (ADRs)

| ADR | Decision | Rationale | Status |
|---|---|---|---|
| ADR-001 | FastAPI over Django | Async-first, Pydantic native, lower overhead | ✅ Accepted |
| ADR-002 | Cassandra for event log | Write throughput, TTL, immutability | ✅ Accepted |
| ADR-003 | AWS KMS envelope encryption | No self-managed key material | ✅ Accepted |
| ADR-004 | BentoML over TorchServe | Simpler ops, multi-framework | ✅ Accepted |
| ADR-005 | Neo4j for entity graph | Native graph traversal, Cypher | ✅ Accepted |
| ADR-006 | Redis sliding window for velocity | Sub-ms, atomic ZADD operations | ✅ Accepted |
| ADR-007 | Istio mTLS over manual certs | Zero-touch cert rotation, observability | ✅ Accepted |

---

## Technology Stack Reference

### Application
| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.12+ |
| API Framework | FastAPI | 0.111+ |
| Validation | Pydantic | v2 |
| ORM | SQLAlchemy (async) | 2.0+ |
| Migrations | Alembic | 1.13+ |
| Task Queue | Celery | 5.x |
| HTTP Client | httpx | 0.27+ |
| Logging | structlog | 24.x |

### Data
| Role | Technology |
|---|---|
| Primary DB | PostgreSQL 16 + pgvector |
| Event Log | Apache Cassandra 5 |
| Cache / Velocity | Redis 7 (Cluster) |
| Graph | Neo4j 5 (AuraDB) |
| Search | Elasticsearch 8 |
| Warehouse | Snowflake |

### ML
| Role | Technology |
|---|---|
| Feature Store | Feast |
| Training | XGBoost · LightGBM · PyTorch |
| Serving | BentoML |
| Experiments | MLflow |
| Drift Detection | Evidently AI |
| Pipelines | PySpark · Apache Kafka |

### Infrastructure
| Role | Technology |
|---|---|
| Orchestration | Kubernetes 1.30 (EKS) |
| Service Mesh | Istio + Envoy |
| IaC | Terraform + Helm |
| GitOps | ArgoCD |
| CI | GitHub Actions |
| Registry | AWS ECR |

### Observability
| Role | Technology |
|---|---|
| Metrics | Prometheus + Grafana |
| Tracing | OpenTelemetry + Jaeger |
| Logging | Loki + Grafana |
| Alerting | PagerDuty + Alertmanager |
| Errors | Sentry |

### Security
| Role | Technology |
|---|---|
| Secrets | HashiCorp Vault |
| Identity | Keycloak (OIDC) |
| API Gateway | Kong Gateway |
| WAF | Cloudflare / AWS WAF |
| KMS | AWS KMS |
| SAST | Bandit + Semgrep |
| Dependency | Snyk + Trivy |

---

## Current Sprint (Sprint 3)

- [ ] Rule Engine v1 — 10 production rules
- [ ] Feast feature store (online + offline)
- [ ] PostgreSQL schema migrations complete
- [ ] BentoML inference server wired to scoring API
- [ ] Prometheus + Grafana dashboards live
- [ ] Integration test suite — target 85% coverage

## Open Issues

| ID | Issue | Owner | Priority |
|---|---|---|---|
| ISS-001 | ML model cold-start latency > 300ms | `@yuki` | P1 |
| ISS-002 | PgBouncer pool exhaustion under load | `@sofia` | P1 |
| ISS-003 | Vault secret rotation not wired to app reload | `@priya` | P2 |
| ISS-004 | Neo4j 3-hop traversal timeout | `@marcus` | P2 |
| ISS-005 | Missing runbook: Cassandra node failure | `@darius` | P2 |

---

## Agent Interaction Rules

1. Stay in character — each agent has a distinct voice and background.
2. Reference real technologies, RFCs, and standards — no vague answers.
3. Disagree constructively — agents may challenge each other's proposals.
4. Escalate cross-domain issues — explicitly hand off to the right agent.
5. Prioritize production correctness — never suggest shortcuts that fail at scale.
6. Code must be runnable — no pseudocode in final answers.
7. Cite ADRs when relevant — decisions are documented for a reason.

---

*Owner: Engineering Leadership*
*Review Cycle: Per Sprint*
*Classification: Internal — Engineering Confidential*