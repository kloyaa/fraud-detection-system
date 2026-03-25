# Capacity Planning Model
## Risk Assessment System (RAS) — Infrastructure Sizing & Scaling Strategy

```yaml
document:       docs/architecture/capacity_plan.md
version:        1.0.0
owners:         Marcus Chen (@marcus) — Chief Risk Architect
                Darius Okafor (@darius) — Staff SRE / Platform Engineer
reviewers:      "@sofia · @yuki · @james"
last_updated:   Pre-development
status:         Approved — revision to be scheduled post load test
horizon:        12 months (2024-Q2 → 2025-Q2)
classification: Internal — Engineering Confidential
```

---

## 1. Purpose

This document defines the capacity model for RAS — traffic projections, infrastructure sizing, scaling thresholds, cost estimates, and the methodology for revising the model as production data arrives.

> *@marcus:* "Capacity planning is not a one-time exercise. It is a living model. The projections here are based on merchant pipeline data, historical transaction patterns from comparable systems, and our SLA commitments. Every assumption is documented. When production data contradicts an assumption, we update the model — not the SLA."

> *@darius:* "Every number in this document has a corresponding Kubernetes HPA threshold, a PagerDuty alert, and a cost line in our cloud budget. Capacity planning that lives only in a spreadsheet is not capacity planning — it is wishful thinking."

---

## 2. Traffic Projections

### 2.1 Transaction Volume Forecast

| Period | Peak TPS | Daily Transactions | Monthly Transactions | Basis |
|---|---|---|---|---|
| **GA (Q2 2024)** | 5,000 | 150M | 4.5B | 3 launch merchants |
| **Q3 2024** | 15,000 | 450M | 13.5B | 10 merchants onboarded |
| **Q4 2024** | 35,000 | 1.05B | 31.5B | Holiday peak + 25 merchants |
| **Q1 2025** | 25,000 | 750M | 22.5B | Post-holiday normalisation |
| **Q2 2025** | 50,000 | 1.5B | 45B | 50 merchants + organic growth |
| **Stress target** | 100,000 | — | — | 2x Q2 2025 peak — design ceiling |

**Traffic shape assumptions:**
- Peak hour: 2x daily average TPS
- Peak minute within peak hour: 3x daily average TPS
- Weekend peak: 1.4x weekday peak (e-commerce pattern)
- Holiday peak (Black Friday, Cyber Monday): 4x daily average TPS
- Fraud attempt rate: 0.12% of transactions → case queue ≈ 67,500 cases/day at 50k TPS

### 2.2 Traffic Distribution by Region

| Region | GA | Q4 2024 | Q2 2025 |
|---|---|---|---|
| `us-east-1` | 70% | 60% | 55% |
| `eu-west-1` | 20% | 28% | 30% |
| `ap-southeast-1` | 10% | 12% | 15% |

**@marcus:** "eu-west-1 and ap-southeast-1 grow faster than us-east-1 as we onboard EU and APAC merchants. Each region must be independently capable of handling 100% of traffic on regional failover — we size all regions to the global peak, not the regional share."

---

## 3. Component Sizing

### 3.1 Scoring API (FastAPI / Kubernetes)

**Sizing model:** Each scoring API pod handles ~500 concurrent requests at P95 < 100ms. At 100% utilisation the pod's event loop would be saturated. We target 65% CPU utilisation for HPA headroom.

| Metric | Value | Derivation |
|---|---|---|
| Requests per pod per second | 500 RPS | Projection based on service design |
| CPU per pod | 2 vCPU | Estimate |
| Memory per pod | 1.5 GB | Pydantic model cache + connection pools |
| Pods at GA (5k TPS) | 3 min → 10 max | 5,000 / 500 = 10 pods |
| Pods at Q2 2025 (50k TPS) | 10 min → 100 max | 50,000 / 500 = 100 pods |
| Pods at stress (100k TPS) | 20 min → 200 max | Design ceiling |

```yaml
# k8s/scoring-api/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ras-scoring-api-hpa
  namespace: risk
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ras-scoring-api
  minReplicas: 3       # Always-on: 3 pods survive AZ failure (1 pod/AZ min)
  maxReplicas: 200     # Stress ceiling
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 65    # Scale at 65% — headroom before saturation
    - type: External
      external:
        metric:
          name: ras_scoring_p95_latency_ms
        target:
          type: AverageValue
          averageValue: "70"        # Scale before breaching 100ms SLO
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30   # React fast on traffic spike
      policies:
        - type: Pods
          value: 10
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300  # Slow scale-down — avoid thrashing
```

**@darius:** "We use dual-metric HPA — CPU utilisation AND P95 latency via a custom metric adapter (Prometheus Adapter). CPU-only HPA scales too late for latency-sensitive workloads. By the time CPU hits 65%, P95 is already at 85ms — we have 15ms left before SLO breach. The latency metric fires earlier, giving us 30 seconds to provision new pods before customers notice."

### 3.2 BentoML Inference Server

| Metric | Value | Derivation |
|---|---|---|
| Inference requests/pod/sec | 2,500 RPS | Adaptive batching: ~50 req/batch × 50 batches/sec |
| CPU per pod | 4 vCPU | XGBoost + LightGBM ensemble |
| GPU per pod | 0.5 A10G (shared) | PyTorch behavioral embedding |
| Memory per pod | 4 GB | Model weights × 3 models + feature vectors |
| Pods at GA | 2 min → 4 max | 5,000 × 0.85 (ML path) / 2,500 = 2 pods |
| Pods at Q2 2025 | 4 min → 20 max | 50,000 × 0.85 / 2,500 = 17 pods |
| Cold-start warmup | 1,000 inferences | ISS-001 open — readiness probe configuration pending |

```yaml
# k8s/bentoml/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ras-bentoml-hpa
spec:
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: External
      external:
        metric:
          name: bentoml_runner_queue_depth
        target:
          type: AverageValue
          averageValue: "50"     # Scale when batch queue exceeds 50 pending
```

### 3.3 PostgreSQL

| Metric | GA | Q2 2025 | Notes |
|---|---|---|---|
| Write TPS (decisions) | 5,000 | 50,000 | One row per scored transaction |
| Read TPS (cases, rules) | 500 | 5,000 | Case management + rule cache reads |
| Storage growth | ~2 GB/day | ~20 GB/day | Estimated row size: 400 bytes |
| Storage at 90 days | 180 GB | 1.8 TB | Decisions table only |
| Instance type (primary) | r7g.2xlarge | r7g.8xlarge | 64 GB RAM — buffer pool sizing |
| Read replicas | 2 | 4 | Analyst queries + case management |
| PgBouncer pool size | 20/pod | 15/pod (more pods) | ISS-002 open: pool_size target=15, pending resolution |
| Max connections | 500 | 2,000 | PgBouncer → PostgreSQL |

**Partitioning strategy (@sofia / @marcus):**
```sql
-- risk_decisions partitioned by month (range on created_at)
-- Each month partition is ~60 GB at Q2 2025 volume
-- Old partitions detached and archived to Snowflake after 90 days

CREATE TABLE risk_decisions (...)
PARTITION BY RANGE (created_at);

CREATE TABLE risk_decisions_2024_04
  PARTITION OF risk_decisions
  FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
```

**@sofia:** "Monthly partitioning gives us three operational benefits: partition pruning makes time-bounded queries 100x faster (analyst queries are always time-bounded), partition detach is instant (vs. DELETE which locks the table), and Snowflake archival is partition-granular — we export and detach one month at a time with zero impact on live traffic."

### 3.4 Cassandra (Event Log)

| Metric | GA | Q2 2025 | Notes |
|---|---|---|---|
| Write TPS | 5,000 | 50,000 | One event per transaction (async) |
| Node count | 6 (2/DC, 3 DCs) | 18 (6/DC, 3 DCs) | RF=3 per DC |
| Storage per node | 2 TB | 4 TB | NVMe SSD |
| Total cluster storage | 12 TB | 72 TB | Before compression (~50% ratio) |
| Effective storage | 6 TB | 36 TB | After lz4 compression |
| 90-day retention (TTL) | Auto | Auto | TTL-based, no manual cleanup |
| Write latency P99 | < 5ms | < 5ms | LSM-tree write path — stable |
| Compaction strategy | TWCS | TWCS | TimeWindowCompactionStrategy — optimal for time-series |

**@darius:** "TimeWindowCompactionStrategy (TWCS) groups SSTables by time window (1 day) and only compacts within the same window. For append-only time-series data with TTL, this is dramatically more efficient than STCS — once a window is fully compacted and past its TTL, it's dropped in a single file delete rather than across multiple SSTables. Compaction overhead is ~15% of write throughput vs. ~40% with STCS at our write patterns."

### 3.5 Redis Cluster (Velocity + Feast)

| Metric | GA | Q2 2025 | Notes |
|---|---|---|---|
| Operations/sec | 100,000 | 1,000,000 | 6 velocity keys × TPS + Feast reads |
| Node count | 6 (3 primary, 3 replica) | 18 (9 primary, 9 replica) | Redis Cluster sharding |
| Memory per primary | 32 GB | 64 GB | r7g.2xlarge → r7g.4xlarge |
| Total memory (primaries) | 96 GB | 576 GB | Velocity keys + Feast features |
| Key count estimate (GA) | 3M | 30M | 6 dims × 500k active customers |
| Avg key size | 200 bytes | 200 bytes | Sorted set metadata |
| Memory for velocity keys | 600 MB | 6 GB | Well within cluster capacity |
| Feast feature memory | ~8 GB | ~80 GB | 47 features × float64 × 2M customers |

**@sofia (ISS-002 context):** "PgBouncer pool exhaustion was at the application level, not Redis. Redis pool sizing: `asyncio-redis` connection pool of 20 per scoring pod × 200 pods (Q2 2025 max) = 4,000 Redis connections total. Redis Cluster supports 10,000+ client connections per node. Not a constraint."

### 3.6 Apache Kafka

| Metric | GA | Q2 2025 | Notes |
|---|---|---|---|
| Broker count | 9 (3/AZ) | 9 (3/AZ) | Broker count driven by partition leadership, not throughput |
| Partitions (risk.decisions) | 24 | 24 | Sized for Q2 2025 — no repartitioning needed |
| Throughput (risk.decisions) | 50 MB/s | 500 MB/s | ~10 KB/msg × TPS |
| Broker instance type | kafka.m5.2xlarge | kafka.m5.4xlarge | Scale up, not out |
| Retention (risk.decisions) | 7 days | 7 days | Snowflake sink for long-term |
| Storage per broker | 2 TB | 8 TB | 7-day retention at Q2 2025 volume |

### 3.7 Neo4j (Entity Graph)

| Metric | GA | Q2 2025 | Notes |
|---|---|---|---|
| Entity nodes | 5M | 50M | Customers + devices + IPs + merchants |
| Relationship edges | 15M | 150M | ~3 edges per entity average |
| Write TPS (async from Flink) | 500 | 5,000 | Graph updates are async — not hot path |
| Query latency (3-hop) | 40–200ms | 40–200ms | Async only — not in scoring path (ADR-005) |
| Instance | AuraDB Professional | AuraDB Enterprise | Managed — @darius ops overhead minimal |

---

## 4. Node Pool Strategy (Kubernetes / Karpenter)

```yaml
# terraform/eks/node_pools.tf

# General purpose — scoring API, case management, admin
node_pool_general:
  instance_types: [r7g.2xlarge, r7g.4xlarge]   # Memory-optimised (Pydantic cache)
  min_nodes:      6                              # 2 per AZ
  max_nodes:      300
  spot_enabled:   true
  spot_fallback:  on_demand                      # Karpenter falls back on spot shortage

# ML inference — BentoML (GPU-backed)
node_pool_ml:
  instance_types: [g5.2xlarge]                  # 1x A10G GPU
  min_nodes:      2                              # 1 per AZ (us-east-1 has 2 AZs with A10G)
  max_nodes:      20
  spot_enabled:   false                          # GPU spot is unreliable — on-demand only
  taint:          nvidia.com/gpu=true:NoSchedule # Only ML pods scheduled here

# Flink stream processing
node_pool_flink:
  instance_types: [c7g.4xlarge]                 # CPU-optimised (stream processing)
  min_nodes:      3
  max_nodes:      30
  spot_enabled:   true

# Monitoring (Prometheus, Grafana, Loki)
node_pool_monitoring:
  instance_types: [m7g.2xlarge]
  min_nodes:      3
  max_nodes:      6
  spot_enabled:   false                          # Monitoring must be stable
```

**Karpenter spot strategy (@darius):**
> "Scoring API pods run on spot instances with on-demand fallback. At our workload profile (stateless, fast startup < 10s), spot interruption is survivable — Karpenter provisions a replacement on-demand node within 2 minutes, HPA maintains minimum pod count, and Kubernetes reschedules. The cost saving is 60–70% vs. on-demand for the scoring pool. GPU nodes are on-demand only — spot GPU availability is too unpredictable for a latency-sensitive ML serving workload."

---

## 5. Scaling Triggers & Runbooks

| Component | Scale-Up Trigger | Scale-Down Trigger | Runbook |
|---|---|---|---|
| Scoring API pods | CPU > 65% OR P95 > 70ms | CPU < 30% for 5 min | HPA automatic |
| BentoML pods | Queue depth > 50 | Queue depth < 10 for 5 min | HPA automatic |
| Cassandra nodes | Disk > 70% OR write latency P99 > 8ms | Manual (data redistribution) | `docs/runbooks/cassandra_scale_out.md` |
| PostgreSQL | CPU > 70% OR replication lag > 1s | Manual (requires downtime for scale-down) | `docs/runbooks/postgres_scale_up.md` |
| Redis nodes | Memory > 70% | Manual (slot rebalancing) | `docs/runbooks/redis_scale_out.md` |
| Kafka brokers | Disk > 70% OR throughput > 80% | Manual | `docs/runbooks/kafka_broker_add.md` |
| Flink TaskManagers | Consumer lag > 2,000 | Consumer lag < 100 for 10 min | Flink autoscaling |

---

## 6. Cost Model

### 6.1 Monthly Infrastructure Cost Estimate (AWS)

| Component | GA (Q2 2024) | Q2 2025 | Notes |
|---|---|---|---|
| EKS nodes (scoring API) | $4,200 | $31,000 | Spot mix — 70% spot savings |
| EKS nodes (BentoML GPU) | $3,800 | $19,000 | On-demand g5.2xlarge |
| EKS nodes (monitoring) | $1,200 | $2,400 | On-demand |
| RDS PostgreSQL (primary + 2 replicas) | $2,800 | $14,000 | r7g.2xlarge → r7g.8xlarge |
| Cassandra (self-managed EC2) | $3,600 | $21,600 | NVMe i3en.3xlarge |
| Redis (ElastiCache) | $1,800 | $12,000 | r7g.2xlarge × 6 → 18 nodes |
| Kafka (Confluent Cloud) | $2,400 | $9,600 | Per-throughput pricing |
| Neo4j (AuraDB) | $800 | $3,200 | Professional → Enterprise |
| Snowflake | $1,200 | $6,000 | Compute credits |
| Cloudflare (Pro + Workers) | $400 | $1,200 | — |
| AWS KMS | $200 | $800 | Per-key + API call pricing |
| Misc (S3, ECR, CloudTrail) | $600 | $2,000 | — |
| **Total monthly** | **$23,000** | **$122,800** | — |
| **Cost per million transactions** | **$5.11** | **$2.73** | Economies of scale |

> *@darius:* "Cost per million transactions drops from $5.11 to $2.73 as we scale — fixed infrastructure costs (monitoring, Kafka brokers, management overhead) are spread over higher volume. The GA cost is artificially high per transaction because of the minimum viable cluster sizing. Break-even on the monitoring layer alone requires ~1B monthly transactions."

### 6.2 Cost Optimisation Actions

| Action | Saving | Timeline | Owner |
|---|---|---|---|
| Spot instances for scoring API pods | -$12,000/mo at Q2 2025 | GA | `@darius` |
| Cassandra TWCS compaction (reduces IOPS) | -$2,400/mo | Pre-development | `@darius` |
| Snowflake auto-suspend (idle warehouse) | -$800/mo | Pre-development | `@yuki` |
| Reserved instances for always-on nodes (3-year) | -$8,000/mo at Q2 2025 | Q3 2024 | `@darius` |
| S3 Intelligent-Tiering for Flink checkpoints | -$300/mo | Pre-development | `@darius` |

---

## 7. Capacity Headroom Targets

At all times, RAS must maintain sufficient headroom to absorb unexpected traffic spikes without SLO degradation:

| Component | Target Headroom | Rationale |
|---|---|---|
| Scoring API CPU | 35% free at peak | HPA needs 30s to provision new pods |
| BentoML queue | < 50% capacity at peak | Batch queue saturation causes latency cliff |
| PostgreSQL connections | 40% free at peak | PgBouncer pool exhaustion = ISS-002 |
| Redis memory | 30% free | OOM eviction would corrupt velocity state |
| Cassandra disk | 30% free | < 20% triggers emergency compaction |
| Kafka disk | 40% free | Retention can spike on consumer lag |
| EKS node capacity | 20% free | Karpenter needs time to provision spot nodes |

---

## 8. Capacity Review Cadence

| Review Type | Frequency | Trigger | Owner |
|---|---|---|---|
| Metrics review | Weekly | Routine | `@darius` |
| Capacity model update | Monthly | Actual vs. projected comparison | `@marcus` + `@darius` |
| Full capacity re-plan | Quarterly | Q-over-Q growth review | `@marcus` + `@darius` |
| Emergency re-plan | Ad hoc | > 50% variance from projection | `@marcus` |
| Pre-merchant onboarding | Per new merchant | Expected traffic contribution | `@marcus` |

**Capacity review checklist (@darius):**
```
Monthly Capacity Review:
  □ Actual peak TPS vs. projected (this document §2.1)
  □ Pod autoscaling events — HPA scale-up frequency
  □ Cassandra disk utilisation trend (30-day)
  □ Redis memory utilisation trend (30-day)
  □ PostgreSQL connection pool peak utilisation
  □ Kafka partition throughput vs. capacity
  □ Cost actual vs. estimate (§6.1)
  □ Karpenter spot interruption rate
  □ Any component approaching headroom threshold (§7)
  □ Update projections if actual deviates > 20% from forecast
```

---

## 9. Disaster Capacity Scenarios

### 9.1 Single AZ Loss (us-east-1)

```
Normal:  3 AZs × 10 scoring pods = 30 pods total
AZ loss: 2 AZs × 10 scoring pods = 20 pods remaining
         → 33% capacity reduction
         → Karpenter provisions replacement pods in remaining AZs: ~2 min
         → Pod Disruption Budget ensures minimum 2 pods survive loss

Impact:  Temporary TPS reduction during pod replacement
         P95 latency may spike during 2-minute recovery window
         No data loss (Cassandra RF=3, min 2 copies in surviving AZs)
```

### 9.2 Full Regional Loss (us-east-1)

```
Normal:    us-east-1 (55%) + eu-west-1 (30%) + ap-southeast-1 (15%)
After:     eu-west-1 (67%) + ap-southeast-1 (33%)  [Cloudflare re-routes]

Each region is sized to handle 100% of global traffic:
  eu-west-1 max capacity: 100k TPS (stress ceiling)
  ap-southeast-1 max capacity: 100k TPS (stress ceiling)

Impact:    ~15-30s traffic re-routing (Cloudflare health check interval)
           In-flight requests in us-east-1 timeout → client retries (idempotency key)
           PostgreSQL: read replicas in eu-west-1 promote (RTO < 5 min)
           Cassandra: LOCAL_QUORUM satisfied by eu-west-1 DC
           Redis: regional cluster, eu-west-1 velocity state is independent

Tested:    ❌ NOT YET — to be scheduled
           Runbook: docs/runbooks/regional_failover.md (DRAFT)
```

### 9.3 Black Friday / Cyber Monday Peak

```
Expected peak: 4x daily average TPS = 200,000 TPS (Q2 2025 baseline × 4)
Stress ceiling: 100,000 TPS (current design)

⚠️  CAPACITY GAP IDENTIFIED:
    Black Friday peak at Q2 2025 volume EXCEEDS current stress ceiling.
    Action required before Q4 2024:
      1. Validate 100k TPS ceiling with load test (Pre-development)
      2. Identify bottleneck at 100k TPS
      3. Plan capacity expansion OR merchant traffic throttling for peak period
      4. @marcus + @darius joint design session — Pre-development

Holiday runbook:    docs/runbooks/holiday_capacity.md (NOT YET CREATED)
Pre-holiday review: 6 weeks before Black Friday → 2024-10-14
```

> *@marcus:* "The Black Friday gap is a known risk. At Q2 2025 volume (50k TPS baseline), a 4x holiday multiplier puts us at 200k TPS — 2x our stress ceiling. We have two options: (1) scale the stress ceiling to 200k TPS before Q4 (significant infrastructure investment), or (2) implement merchant-level rate limiting that gracefully degrades non-critical merchants during peak periods while protecting Tier 1 merchants. Option 2 is my preference — it is cheaper and more operationally controllable. @james needs to review the contractual SLA implications of rate limiting with merchants. This goes to the Architecture Review Board in Pre-development."

---

## 10. Related Documents

| Document | Location | Owner |
|---|---|---|
| System Architecture Overview | `docs/architecture/system_overview.md` | `@marcus` |
| Kafka Topic Design | `docs/architecture/kafka_topics.md` | `@marcus` |
| ADR Log | `docs/architecture/adr/` | `@marcus` |
| Scoring API Deployment | `k8s/scoring-api/` | `@darius` |
| Terraform Node Pools | `terraform/eks/node_pools.tf` | `@darius` |
| Scaling Runbooks | `docs/runbooks/` | `@darius` |
| PRR Performance Gates (§2) | `docs/quality/prr_checklist.md` | `@aisha` |

---

*Document Version: 1.0.0*
*Owners: Marcus Chen (@marcus) · Darius Okafor (@darius)*
*Review Cycle: Monthly (metrics) · Quarterly (full re-plan)*
*Classification: Internal — Engineering Confidential*