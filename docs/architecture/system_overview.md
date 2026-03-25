# System Overview
## Risk Assessment System (RAS) — Architecture Documentation

```yaml
document:       docs/architecture/system_overview.md
version:        1.0.0
owner:          Marcus Chen (@marcus) — Chief Risk Architect
reviewers:      "@priya · @darius · @sofia · @yuki"
last_updated:   Pre-development
status:         Approved
classification: Internal — Engineering Confidential
```

---

## 1. System Purpose

The Risk Assessment System (RAS) is a real-time fraud and risk evaluation platform that evaluates financial transactions, user sessions, and behavioural signals to produce a risk score, enforce policy rules, and trigger automated or human-in-the-loop review workflows.

It is the infrastructure layer that answers one question in under 100 milliseconds:

> *"Should this transaction be approved, challenged, or declined — and why?"*

RAS is designed to operate at the scale and reliability level of the systems that inspired it: Stripe Radar and PayPal's risk engine. It is not a prototype. Every architectural decision documented here is made with the assumption that it must hold at 100,000 transactions per second, across three geographic regions, with 99.99% availability.

---

## 2. Design Principles

These principles govern every architectural decision in RAS. When a proposal conflicts with a principle, an ADR must document the trade-off explicitly.

| # | Principle | Implication |
|---|---|---|
| P1 | **Latency is a first-class constraint** | Every external dependency has a timeout. Scoring must complete in < 100ms P95 regardless of downstream state. |
| P2 | **Fail safely, not silently** | Defined degraded modes for every dependency failure. Failures are observable, not invisible. |
| P3 | **Immutable audit trail** | Every scoring decision is an append-only fact. Nothing is updated — only superseded. |
| P4 | **Separation of concerns** | Write path (scoring) and read path (analytics, case management) are architecturally separated. |
| P5 | **Security at every layer** | No layer trusts another. mTLS between services. Encryption at rest and in transit. No plaintext secrets. |
| P6 | **Compliance by design** | Regulatory obligations (PCI DSS, GDPR, AML) are architectural constraints, not afterthoughts. |
| P7 | **Data gravity** | Compute moves to data, not data to compute. Features are pre-computed and served from the online store. |
| P8 | **Operational simplicity** | A system that cannot be operated at 3am by an on-call engineer is not production-ready. |

---

## 3. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          External Clients                                │
│              Merchant SDK  ·  Internal Services  ·  Webhooks             │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ HTTPS / mTLS
                    ┌────────────▼────────────────┐
                    │       Cloudflare WAF         │
                    │   DDoS Protection · WAF Rules│
                    └────────────┬────────────────┘
                                 │
                    ┌────────────▼────────────────┐
                    │      Kong API Gateway        │
                    │  JWT Auth · Rate Limit · WAF │
                    │  Route: /v1/risk/score        │
                    │  Route: /v1/cases             │
                    │  Route: /v1/rules             │
                    └────────────┬────────────────┘
                                 │ mTLS (Istio)
        ┌────────────────────────┼──────────────────────────┐
        │                        │                          │
┌───────▼────────┐    ┌──────────▼──────────┐    ┌─────────▼──────────┐
│  Scoring API   │    │  Case Mgmt API      │    │  Admin / Config    │
│  (FastAPI)     │    │  (FastAPI + GraphQL)│    │  API (FastAPI)     │
│  /v1/risk/*    │    │  /v1/cases/*        │    │  /v1/rules/*       │
└───────┬────────┘    └──────────┬──────────┘    └─────────┬──────────┘
        │                        │                          │
        │              ┌─────────▼──────────────────────────┤
        │              │         Kafka Event Bus             │
        │              │  topics: risk.decisions             │
        │              │          risk.events                │
        │              │          cases.created              │
        │              │          rules.changed              │
        │              │          model.feedback             │
        │              └──────────┬─────────────────────────┘
        │                         │
        │                ┌────────▼───────────┐
        │                │  Apache Flink       │
        │                │  Stream Processor   │
        │                │  velocity windows   │
        │                │  graph feature agg  │
        │                └────────┬───────────┘
        │                         │
┌───────▼─────────────────────────▼──────────────────────────┐
│                    Scoring Pipeline                          │
│                                                              │
│  [1] Enrichment Service  ──►  IP geo · BIN lookup · Device  │
│  [2] Feature Service     ──►  Feast online store (Redis)    │
│  [3] Rule Engine         ──►  Priority-ordered policy rules │
│  [4] ML Inference        ──►  BentoML (XGBoost + PyTorch)   │
│  [5] Decision Assembly   ──►  Score + decision + reasons    │
│                                                              │
└───────────────────────────────────────────────────────────-─┘
        │
        ├──► Response to client (< 100ms P95)
        ├──► Kafka: risk.decisions topic
        └──► Cassandra: immutable event log
                │
        ┌───────▼──────────────────────────────────────────┐
        │                  Data Stores                      │
        │                                                   │
        │  PostgreSQL 16    — decisions · cases · rules     │
        │  Cassandra 5      — immutable event log           │
        │  Redis 7 Cluster  — velocity · cache · idempotency│
        │  Neo4j 5          — entity graph (async)          │
        │  Elasticsearch 8  — audit log search              │
        │  Snowflake        — warehouse · ML training data  │
        └───────────────────────────────────────────────────┘
```

---

## 4. Scoring Pipeline — Detailed Flow

The scoring pipeline is the critical path. Every millisecond matters. The pipeline is designed so that each stage can degrade independently without failing the entire request.

```
Client Request (POST /v1/risk/score)
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│  STAGE 1: VALIDATION & IDEMPOTENCY (< 1ms)               │
│                                                          │
│  Pydantic v2 strict validation                           │
│  Idempotency key check (Redis SET NX)                    │
│  JWT scope enforcement (risk:score)                      │
│  If idempotency hit → return cached response             │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│  STAGE 2: ENRICHMENT (target: < 10ms · timeout: 50ms)    │
│                                                          │
│  IP Geolocation    → MaxMind GeoIP2 (local DB)           │
│  IP Proxy Score    → IPQualityScore API                  │
│  BIN Lookup        → Internal BIN database               │
│  Device Fp Match   → Device fingerprint service          │
│                                                          │
│  DEGRADATION: timeout → score with available data        │
│               flag:   enrichment_partial = true          │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│  STAGE 3: FEATURE EXTRACTION (target: < 5ms)             │
│                                                          │
│  Feast online store (Redis) — pre-computed features:     │
│    velocity:  txn_count_60s, txn_amount_1h               │
│    graph:     device_account_count_7d (async Neo4j)      │
│    history:   customer_avg_amount_30d                    │
│    merchant:  merchant_fraud_rate_30d                    │
│                                                          │
│  Derived features computed inline:                       │
│    amount_vs_avg_ratio, ip_country_mismatch              │
│    bin_country_mismatch, hour_of_day                     │
│                                                          │
│  DEGRADATION: Feast miss → score with available features │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│  STAGE 4: RULE ENGINE (target: < 2ms)                    │
│                                                          │
│  Priority-ordered rule evaluation                        │
│                                                          │
│  Priority 1–4:  BLOCK rules (hard stops)                 │
│    R001 Blocked Country                                  │
│    R002 Velocity Exceeded                                │
│    R010 Known Fraud Device                               │
│    R011 Consortium Block                                 │
│                                                          │
│  Priority 5–7:  CHALLENGE rules                          │
│    R003 Amount Spike                                     │
│    R004 New Device High Value                            │
│    R012 Cross-Border High Value                          │
│                                                          │
│  Priority 8+:  ALLOW rules (fast-path bypass)            │
│    R020 Low-Risk Trusted Merchant                        │
│                                                          │
│  Outcome:                                                │
│    BLOCK  → decline immediately, skip ML                 │
│    ALLOW  → approve immediately, skip ML                 │
│    SCORE  → continue to ML (85% of traffic)             │
└───────────────────────────┬──────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
           BLOCK          ALLOW         SCORE
              │             │             │
              ▼             ▼             ▼
           decline       approve    ┌────────────────────────┐
                                    │  STAGE 5: ML SCORING   │
                                    │  (target: < 25ms)      │
                                    │                        │
                                    │  XGBoost fraud scorer  │
                                    │  Behavioral embedding  │
                                    │  Device risk model     │
                                    │  Ensemble: weighted avg│
                                    │                        │
                                    │  Output: 0–1000 score  │
                                    │                        │
                                    │  DEGRADATION:          │
                                    │  BentoML 503 →         │
                                    │  rule-only fallback    │
                                    └────────────┬───────────┘
                                                 │
                                                 ▼
┌──────────────────────────────────────────────────────────┐
│  STAGE 6: DECISION ASSEMBLY (< 1ms)                      │
│                                                          │
│  Score < 200   → APPROVE                                 │
│  Score 200–600 → CHALLENGE (3DS · OTP · biometric)       │
│  Score > 600   → DECLINE                                 │
│  Score > 600   → CREATE CASE (human review queue)        │
│                                                          │
│  Assemble response:                                      │
│    request_id, score, decision, reasons,                 │
│    rules_triggered, challenge_type, processing_ms,       │
│    model_version                                         │
└───────────────────────────┬──────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────────┐
        │                   │                       │
        ▼                   ▼                       ▼
  Response to          Kafka publish           Cassandra write
  client               risk.decisions          (async, non-blocking)
  (synchronous)        (async)                 (async)
```

---

## 5. Data Architecture

### 5.1 Database Selection Rationale

Each data store is chosen for a specific access pattern. Using the wrong store for a pattern is a design error that compounds under load. (See ADR-002, ADR-005, ADR-006.)

| Store | Role | Access Pattern | Why This Store |
|---|---|---|---|
| **PostgreSQL 16** | Decisions · Cases · Rules · Config | Relational queries, ACID transactions, complex joins | ACID compliance, JSON support, pgvector for embeddings |
| **Cassandra 5** | Immutable event log | Append-only, high write throughput, time-series by customer | 50k+ TPS writes, TTL-based retention, multi-DC replication |
| **Redis 7 Cluster** | Velocity counters · Idempotency · Cache | Sub-ms atomic operations, sorted sets, TTL | Atomic ZADD for sliding windows, in-memory speed |
| **Neo4j 5** | Entity relationship graph | Graph traversal, fraud ring detection | Native graph engine, Cypher query language |
| **Elasticsearch 8** | Audit log search · Analyst queries | Full-text search, aggregations | Inverted index, analyst-facing query interface |
| **Snowflake** | Data warehouse · ML training | Batch analytics, large-scale aggregation | Column-store, PySpark integration, ML feature backfill |

### 5.2 Data Flow by Category

```
TRANSACTION DATA FLOW
─────────────────────
Client → Scoring API → [scored] → Kafka risk.decisions
                                → PostgreSQL risk_decisions (OLTP)
                                → Cassandra risk.events (audit log)
                                → Elasticsearch (search index, async)

FEATURE DATA FLOW
─────────────────
Kafka risk.decisions → Flink → Redis (Feast online store)
                              velocity: txn_count_60s, txn_amount_1h

Kafka risk.decisions → Flink → Neo4j → Flink → Redis (Feast)
                              graph:  device_account_count_7d

PySpark (batch, hourly) → Snowflake → Redis (Feast)
                         history: customer_avg_amount_30d

CASE DATA FLOW
──────────────
Scoring decision (score > 600) → PostgreSQL cases table
                               → Kafka cases.created
                               → Case Management API
                               → [Analyst resolves]
                               → Kafka model.feedback
                               → @yuki training pipeline

AUDIT DATA FLOW
───────────────
Every decision → Cassandra risk.events (immutable, 90-day TTL)
              → Elasticsearch (searchable, 1-year retention)
              → Snowflake (cold storage, 7-year compliance retention)
```

### 5.3 Velocity Counter Design (Redis Sliding Window)

The velocity service implements a sorted-set sliding window per entity per time window. This is the highest-throughput Redis pattern in RAS, executing on every scoring request.

```python
# Per-customer velocity: transactions in last 60 seconds
key:   "vel:txn:{customer_id}:60"
type:  Redis Sorted Set (ZADD)
score: unix timestamp (float)
value: unique transaction ID

# Atomic pipeline per request:
ZREMRANGEBYSCORE key 0 (now - 60)   # Remove expired members
ZADD key now txn_id                  # Add current transaction
ZCARD key                            # Count = velocity in window
EXPIRE key 61                        # TTL = window + 1s

# Velocity dimensions tracked:
vel:txn:{customer_id}:60             # Txns per customer, 60s
vel:txn:{customer_id}:3600           # Txns per customer, 1h
vel:amt:{customer_id}:3600           # Amount per customer, 1h
vel:txn:{merchant_id}:60             # Txns per merchant, 60s
vel:txn:{device_fp}:300              # Txns per device, 5min
vel:txn:{ip_address}:60              # Txns per IP, 60s
```

---

## 6. Multi-Region Topology

RAS operates active-active across three geographic regions. Every region is capable of independently processing 100% of traffic.

```
                    ┌──────────────────┐
                    │   Cloudflare     │
                    │ Global LB        │
                    │ Latency routing  │
                    └────────┬─────────┘
           ┌─────────────────┼──────────────────┐
           │                 │                  │
           ▼                 ▼                  ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  us-east-1   │  │  eu-west-1   │  │ ap-southeast-1│
  │  PRIMARY     │  │  SECONDARY   │  │  SECONDARY   │
  │              │  │              │  │              │
  │  EKS Cluster │  │  EKS Cluster │  │  EKS Cluster │
  │  3–50 pods   │  │  3–50 pods   │  │  3–50 pods   │
  │              │  │              │  │              │
  │  PostgreSQL  │  │  PostgreSQL  │  │  PostgreSQL  │
  │  (primary)   │  │  (replica)   │  │  (replica)   │
  │              │  │              │  │              │
  │  Cassandra   ◄─────────────────────► Cassandra   │
  │  (3 nodes)   │  │  (3 nodes)   │  │  (3 nodes)   │
  │  RF=3 multi  │  │  DC strategy │  │              │
  │              │  │              │  │              │
  │  Redis       │  │  Redis       │  │  Redis       │
  │  Cluster     │  │  Cluster     │  │  Cluster     │
  │  (regional)  │  │  (regional)  │  │  (regional)  │
  │              │  │              │  │              │
  │  Kafka       ◄──┤ MirrorMaker2 ├──► Kafka        │
  │  (9 brokers) │  │              │  │  (9 brokers) │
  └──────────────┘  └──────────────┘  └──────────────┘

Traffic routing:    Latency-based (Cloudflare)
Failover:           Automatic on health check failure (< 30s)
Data consistency:   Eventual (Cassandra multi-DC, Kafka MM2)
RPO:                < 1 second (normal ops)
RTO:                < 5 minutes (regional failure)
```

### Regional Failover Sequence

```
1. us-east-1 health degraded
2. Cloudflare detects failure (10–15s health check interval)
3. Traffic routes to eu-west-1 and ap-southeast-1
4. In-flight requests in us-east-1: timed out → client retries with idempotency key
5. eu-west-1 Kafka MirrorMaker2 lag: 1–3s (within RPO)
6. Cassandra reads: LOCAL_QUORUM → eu-west-1 DC serves from local replicas
7. PostgreSQL: read replicas promote (RTO: < 5 min for primary promotion)
8. PagerDuty alert fires → @darius on-call paged
9. Runbook: docs/runbooks/regional_failover.md
```

---

## 7. Service Boundaries & Responsibilities

| Service | Language | Owns | Does NOT Own |
|---|---|---|---|
| **Scoring API** | Python / FastAPI | Request validation, pipeline orchestration, response assembly | ML model weights, rule definitions, feature computation |
| **Rule Engine** | Python (embedded) | Rule evaluation, priority ordering, action dispatch | Rule authoring, ML scoring |
| **ML Inference Service** | Python / BentoML | Model serving, adaptive batching, A/B routing | Model training, feature engineering |
| **Feature Service** | Python / Feast | Online feature serving (Redis), feature versioning | Feature computation, pipeline |
| **Velocity Service** | Python / Redis | Sliding window counters, velocity checks | Enrichment, ML scoring |
| **Enrichment Service** | Python / httpx | IP geo, BIN lookup, device fingerprint matching | Risk scoring |
| **Graph Risk Service** | Python / Neo4j | Entity relationship queries (async only) | Real-time scoring path |
| **Case Management API** | Python / FastAPI | Analyst queue, case CRUD, resolution workflow | Scoring, ML inference |
| **Flink Pipeline** | Java / Python | Real-time feature aggregation, stream processing | Batch features, model training |
| **Admin API** | Python / FastAPI | Rule management, model promotion, config | Transaction processing |

---

## 8. Architectural Decision Records (ADRs)

All ADRs are stored in `docs/architecture/adr/`. The following decisions govern this architecture:

| ADR | Title | Decision | Date | Status |
|---|---|---|---|---|
| ADR-001 | API Framework | FastAPI over Django REST Framework | Pre-development | ✅ Accepted |
| ADR-002 | Event Log Storage | Cassandra over PostgreSQL for audit log | Pre-development | ✅ Accepted |
| ADR-003 | Encryption Key Management | AWS KMS envelope encryption over self-managed keys | Pre-development | ✅ Accepted |
| ADR-004 | ML Serving Framework | BentoML over TorchServe / Seldon | Pre-development | ✅ Accepted |
| ADR-005 | Graph Store | Neo4j for entity graph (async only, not hot path) | Pre-development | ✅ Accepted |
| ADR-006 | Velocity Counter Implementation | Redis sorted-set sliding window over Kafka Streams | Pre-development | ✅ Accepted |
| ADR-007 | Service Mesh | Istio mTLS over manual certificate management | Pre-development | ✅ Accepted |
| ADR-008 | Rule Distribution | Kafka-based rule refresh over Redis cache TTL | Pre-development | ✅ Accepted |

### ADR-002: Cassandra over PostgreSQL for Event Log (Summary)

**Context:** The RAS audit log must support 50k+ TPS writes, 90-day retention on 150B+ records per year, and immutable append-only semantics.

**Decision:** Apache Cassandra 5 with `(customer_id, occurred_at TIMEUUID)` primary key, `LOCAL_QUORUM` consistency, and TTL-based retention.

**Rationale:** PostgreSQL MVCC vacuum lag degrades at sustained 50k TPS write throughput on a table with 150B+ rows. Cassandra's LSM-tree storage engine handles this write pattern natively. The `TIMEUUID` clustering key gives time-ordered reads per customer with sub-5ms P99. TTL handles the 90-day retention policy without a separate deletion job.

**Trade-offs accepted:** No ACID transactions across tables. Cassandra is not a relational store — it is an event log. Analytical queries go to Snowflake (cold path). Cassandra is never queried for JOINs.

---

## 9. Latency Budget

The scoring API SLA is P95 < 100ms. Every pipeline stage has an allocated latency budget:

| Stage | Budget | Target (P50) | Notes |
|---|---|---|---|
| Validation + Idempotency | 1ms | < 1ms | — |
| Enrichment | 10ms | < 10ms | — |
| Feature Extraction (Feast) | 5ms | < 5ms | — |
| Rule Engine | 2ms | < 2ms | — |
| ML Inference (BentoML) | 25ms | < 25ms | ISS-001 open: cold-start > 300ms |
| Decision Assembly | 1ms | < 1ms | — |
| Network + Serialization | 8ms | < 8ms | — |
| **Total P50** | **52ms** | **< 35ms (target)** | — |
| **Total P95 target** | **100ms** | **< 100ms (SLA)** | — |

**Budget allocation principle (@marcus):** The ML inference stage owns the largest budget (25ms) because it is the highest-value stage and the hardest to optimise. Network overhead (8ms) is fixed. All other stages must stay within their budgets to protect the ML allocation. ISS-001 (BentoML cold-start > 300ms) is open — readiness probe configuration required before production.

---

## 10. Degradation Modes

RAS defines explicit degraded operational modes for every critical dependency failure. These are tested in chaos experiments (see `@darius`'s chaos catalog) and documented in runbooks.

| Failure | Degraded Mode | Impact | Recovery |
|---|---|---|---|
| BentoML 503 / timeout | Rule-only scoring | ML score unavailable — rule decisions only | BentoML restarts, circuit breaker resets |
| Redis unavailable | Velocity checks fail open | No velocity enforcement, flag on decision | Redis cluster recovers, counters rebuild |
| Enrichment timeout | Score with partial features | Reduced ML accuracy, flag on decision | Enrichment service recovers |
| Feast miss (feature) | Score with available features | Partial feature vector, flag on decision | Feast Redis re-warms |
| Cassandra write failure | Buffer to Kafka DLQ | Audit log delayed, not lost | Cassandra recovers, DLQ replays |
| PostgreSQL primary failure | Read replicas serve reads | Writes queue, no new cases created | Replica promotes (< 5 min) |
| Neo4j unavailable | Serve stale graph features from Feast | Graph features may be up to 1h stale | Neo4j recovers, Flink backfills |

> **@marcus:** Every degraded mode must be tested before production. A degraded mode that is only defined in a document is not a degraded mode — it is a wishful description of an untested failure. See chaos experiment catalog in `@darius`'s agent file.

---

## 11. Key Metrics & SLA Targets

| Metric | Target | Alert Threshold |
|---|---|---|
| Availability | 99.99% | < 99.95% over 5 min |
| P50 Scoring Latency | < 35ms | > 50ms for 5 min |
| P95 Scoring Latency | < 100ms | > 120ms for 3 min |
| P99 Scoring Latency | < 250ms | > 300ms for 3 min |
| Error Rate | < 0.1% | > 0.5% for 2 min |
| ML Fallback Rate | < 0.5% | > 2% for 5 min |
| Kafka Consumer Lag | < 500ms | > 2,000ms for 3 min |
| Case Queue Depth | < 500 | > 1,000 |
| False Positive Rate | < 5% | > 7.5% over 24h |
| RPO | < 1 second | — |
| RTO | < 5 minutes | — |

---

## 12. Related Documents

| Document | Location | Owner |
|---|---|---|
| ADR Log | `docs/architecture/adr/` | `@marcus` |
| Kafka Topic Design | `docs/architecture/kafka_topics.md` | `@marcus` |
| Capacity Planning Model | `docs/architecture/capacity_plan.md` | `@marcus` |
| Threat Model (STRIDE) | `docs/security/threat_model.md` | `@priya` |
| ML Pipeline Architecture | `docs/ml/pipeline_architecture.md` | `@yuki` |
| Model Card | `docs/ml/model_card.md` | `@yuki` |
| PCI DSS Controls | `docs/compliance/pci_dss_controls.md` | `@james` |
| GDPR DPIA | `docs/compliance/gdpr_dpia.md` | `@james` |
| Runbook Library | `docs/runbooks/` | `@darius` |
| PRR Checklist | `docs/quality/prr_checklist.md` | `@aisha` |

---

*Document Version: 1.0.0*
*Owner: Marcus Chen — Chief Risk Architect*
*Review Cycle: Per Sprint · Major Review: Quarterly*
*Classification: Internal — Engineering Confidential*