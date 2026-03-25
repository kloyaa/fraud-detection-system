# Kafka Topic Design
## Risk Assessment System (RAS) — Event Streaming Architecture

```yaml
document:       docs/architecture/kafka_topics.md
version:        1.0.0
owner:          Marcus Chen (@marcus) — Chief Risk Architect
reviewers:      "@darius · @sofia · @yuki · @priya · @james"
last_updated:   Pre-development
status:         Approved
broker:         Confluent Cloud (9 brokers · 3 AZs per region)
regions:        us-east-1 · eu-west-1 · ap-southeast-1
classification: Internal — Engineering Confidential
```

---

## 1. Design Principles

Kafka is the **system of record for everything that ever happened in RAS**. These principles govern all topic design decisions:

| # | Principle | Implication |
|---|---|---|
| K1 | **Topics are append-only facts** | No compaction on audit topics. Events are immutable. |
| K2 | **Schema first** | Every topic has an Avro schema registered in Confluent Schema Registry before first publish. No untyped JSON on the wire. |
| K3 | **Partition by the entity that must be ordered** | Messages about the same customer must land on the same partition to guarantee ordering per customer. |
| K4 | **Consumers are idempotent** | Any consumer must handle duplicate delivery (at-least-once semantics) without side effects. |
| K5 | **Dead Letter Queues for every topic** | Every consumer has a corresponding DLQ topic. Failed messages are never silently dropped. |
| K6 | **Retention is a compliance decision** | Retention periods are set by @james based on regulatory requirements, not by engineering convenience. |
| K7 | **Sensitive fields are encrypted before publish** | No PAN, CVV, or raw PII on any Kafka topic. Field-level encryption applied at the producer before the message leaves the application. |

---

## 2. Cluster Configuration

### 2.1 Broker Topology

```
Confluent Cloud — Dedicated Cluster (per region)
  Brokers:          9 per region (3 per AZ)
  Replication:      RF = 3 (data survives loss of 1 AZ)
  Min ISR:          2 (write fails if < 2 replicas in sync)
  Acks:             all (producer waits for all ISR replicas)
  Compression:      lz4 (CPU-efficient, good compression ratio)
  Max message size: 1 MB (scoring payloads are < 10 KB)
```

### 2.2 Cross-Region Replication

```
us-east-1  ──MirrorMaker2──►  eu-west-1
us-east-1  ──MirrorMaker2──►  ap-southeast-1

Replicated topics:   risk.decisions · risk.events · cases.created
Non-replicated:      Internal ops topics (metrics, heartbeats)

Replication lag target:  < 3 seconds (RPO)
MirrorMaker2 config:
  replication.factor: 3
  offset.translation: true   (consumer offsets translated across clusters)
```

### 2.3 Schema Registry

```
Confluent Schema Registry — one instance per region, cross-region sync
Schema format:    Avro (binary, compact)
Compatibility:    BACKWARD (new schema can read old messages)
                  Producers update schemas → consumers can still read old messages
                  Breaking changes require schema version increment + migration plan

Registry URL:     https://schema-registry.ras.internal:8081
Auth:             RBAC — producers: schema:write · consumers: schema:read
```

---

## 3. Topic Catalogue

### 3.1 `risk.decisions`

**Purpose:** Every scoring decision produced by the Scoring API. The primary event stream for RAS — downstream systems derive their state from this topic.

```yaml
topic:              risk.decisions
partitions:         24
replication_factor: 3
retention:          7 days (hot) — Snowflake sink for long-term
cleanup_policy:     delete
partition_key:      customer_id
compression:        lz4
producers:          ras-scoring-api
consumers:          ras-flink-pipeline      (velocity feature update)
                    ras-case-service        (case creation trigger)
                    ras-ml-feedback         (training label collection)
                    snowflake-sink          (data warehouse)
                    elasticsearch-sink      (audit search index)
cross_region:       replicated via MirrorMaker2
dlq:                risk.decisions.dlq
```

**Avro Schema:**
```json
{
  "type": "record",
  "name": "RiskDecision",
  "namespace": "io.ras.events.v1",
  "fields": [
    {"name": "request_id",        "type": "string"},
    {"name": "customer_id",       "type": "string"},
    {"name": "merchant_id",       "type": "string"},
    {"name": "session_id",        "type": "string"},
    {"name": "amount_cents",      "type": "long"},
    {"name": "currency",          "type": "string"},
    {"name": "score",             "type": "int"},
    {"name": "decision",          "type": {"type": "enum", "name": "Decision",
                                   "symbols": ["approve","challenge","decline"]}},
    {"name": "rules_triggered",   "type": {"type": "array", "items": "string"}},
    {"name": "model_version",     "type": "string"},
    {"name": "processing_ms",     "type": "int"},
    {"name": "requires_review",   "type": "boolean"},
    {"name": "challenge_type",    "type": ["null", "string"], "default": null},
    {"name": "enrichment_partial","type": "boolean", "default": false},
    {"name": "occurred_at",       "type": {"type": "long",
                                   "logicalType": "timestamp-millis"}},
    {"name": "region",            "type": "string"},
    {"name": "schema_version",    "type": "string", "default": "1.0.0"}
  ]
}
```

**Partition strategy:**
Keyed by `customer_id` (Murmur2 hash % 24 partitions). Guarantees all events for a customer land on the same partition — Flink velocity window computation is partition-local, requiring no cross-partition coordination.

**Sensitive field handling (@priya):**
`amount_cents` is stored as integer cents (not decimal) — no PAN, card number, or raw PII in this topic. The `customer_id` is a pseudonymous UUID, not a name or email. BIN data is excluded — BIN enrichment is ephemeral to the scoring pipeline only.

---

### 3.2 `risk.events`

**Purpose:** Fine-grained internal pipeline events — enrichment results, rule evaluations, ML scores. Used by Flink for feature computation and by Evidently AI for model monitoring. More verbose than `risk.decisions`.

```yaml
topic:              risk.events
partitions:         24
replication_factor: 3
retention:          3 days
cleanup_policy:     delete
partition_key:      customer_id
compression:        lz4
producers:          ras-scoring-api (per pipeline stage)
consumers:          ras-flink-pipeline     (feature aggregation)
                    ras-evidently-sink     (model drift monitoring)
cross_region:       not replicated (internal telemetry only)
dlq:                risk.events.dlq
```

**Event types on this topic:**

| `event_type` | Producer Stage | Contents |
|---|---|---|
| `enrichment_completed` | Stage 2 | IP geo, proxy score, BIN metadata, device fingerprint |
| `features_extracted` | Stage 3 | All 47 feature values (point-in-time snapshot) |
| `rule_evaluated` | Stage 4 | Rule ID, condition result, action, evaluation latency |
| `ml_scored` | Stage 5 | Ensemble score, per-model scores, top-4 SHAP values |
| `decision_assembled` | Stage 6 | Final score, decision, processing_ms |

**@yuki:** "The `features_extracted` event is the most valuable for model monitoring. Evidently AI consumes this topic and computes PSI (Population Stability Index) per feature in real time. A PSI > 0.20 on any top-10 feature triggers a Grafana alert and potentially a model retraining. This is how we detect `ip_proxy_score` drift before it degrades model performance."

---

### 3.3 `cases.created`

**Purpose:** Triggers case management workflows when a scoring decision meets case creation criteria (score > 600, rule CR001–CR007 triggered). Consumed by the Case Management API to create the PostgreSQL case record and notify analysts.

```yaml
topic:              cases.created
partitions:         12
replication_factor: 3
retention:          7 days
cleanup_policy:     delete
partition_key:      merchant_id  (cases grouped by merchant for analyst routing)
compression:        lz4
producers:          ras-scoring-api (Stage 6 — post-decision)
consumers:          ras-case-service    (case record creation)
                    ras-sla-monitor     (SLA deadline tracking)
                    ras-pagerduty-sink  (breach notifications)
cross_region:       replicated via MirrorMaker2
dlq:                cases.created.dlq
```

**Avro Schema:**
```json
{
  "type": "record",
  "name": "CaseCreated",
  "namespace": "io.ras.cases.v1",
  "fields": [
    {"name": "case_trigger_id",   "type": "string"},
    {"name": "request_id",        "type": "string"},
    {"name": "decision_id",       "type": "string"},
    {"name": "customer_id",       "type": "string"},
    {"name": "merchant_id",       "type": "string"},
    {"name": "score",             "type": "int"},
    {"name": "decision",          "type": "string"},
    {"name": "triggered_rules",   "type": {"type": "array", "items": "string"}},
    {"name": "compliance_flags",  "type": {"type": "array", "items": "string"}},
    {"name": "sla_priority",      "type": {"type": "enum", "name": "Priority",
                                   "symbols": ["P1","P2","P3"]}},
    {"name": "sla_deadline_ms",   "type": {"type": "long",
                                   "logicalType": "timestamp-millis"}},
    {"name": "occurred_at",       "type": {"type": "long",
                                   "logicalType": "timestamp-millis"}}
  ]
}
```

**SLA priority assignment (at publish time):**

| Condition | Priority | SLA |
|---|---|---|
| `score > 800` | P1 | 2 hours |
| `score 600–800` | P2 | 4 hours |
| `compliance_flags` non-empty (AML) | P1 (override) | Per @james protocol |
| `score < 600` with CR005–CR007 | P3 | 24 hours |

---

### 3.4 `rules.changed`

**Purpose:** Distributes rule definition changes from the Admin API to all scoring pods. Each scoring pod is a consumer and refreshes its in-process rule cache on message receipt. (ADR-008 — Accepted, Pre-development.)

```yaml
topic:              rules.changed
partitions:         1          # Single partition — total ordering required
replication_factor: 3
retention:          30 days    # New pods replay to get full rule history
cleanup_policy:     delete
partition_key:      rule_id
compression:        lz4
producers:          ras-admin-api
consumers:          ras-scoring-api (all pods — in-process rule cache refresh)
cross_region:       replicated via MirrorMaker2
dlq:                rules.changed.dlq
```

**Why single partition:** Rule changes must be applied in total order by all scoring pods. Multiple partitions would allow pods to apply rule changes in different sequences — a pod consuming partition 0 could apply rule R002 before R001 if they were published to different partitions. Single partition guarantees all pods see the same sequence.

**Avro Schema:**
```json
{
  "type": "record",
  "name": "RuleChanged",
  "namespace": "io.ras.rules.v1",
  "fields": [
    {"name": "rule_id",       "type": "string"},
    {"name": "version",       "type": "int"},
    {"name": "action",        "type": {"type": "enum", "name": "RuleAction",
                               "symbols": ["create","update","disable","delete"]}},
    {"name": "changed_by",    "type": "string"},
    {"name": "change_reason", "type": "string"},
    {"name": "occurred_at",   "type": {"type": "long",
                               "logicalType": "timestamp-millis"}}
  ]
}
```

**Note:** The message contains only a pointer (`rule_id`, `version`) — not the full rule definition. Consuming pods re-read the rule definition from PostgreSQL. This keeps Kafka as the notification mechanism and PostgreSQL as the authoritative rule store.

---

### 3.5 `model.feedback`

**Purpose:** Collects ground-truth outcome labels for ML model retraining. Published when analyst resolves a case, when a chargeback webhook is received, or when a merchant submits feedback via the API.

```yaml
topic:              model.feedback
partitions:         12
replication_factor: 3
retention:          90 days    # Full training cycle retention
cleanup_policy:     delete
partition_key:      request_id
compression:        lz4
producers:          ras-case-service      (analyst resolution)
                    ras-chargeback-worker (chargeback webhook processing)
                    ras-scoring-api       (merchant feedback endpoint)
consumers:          ras-ml-training       (label collection for retraining)
                    ras-model-monitor     (false positive/negative tracking)
cross_region:       replicated via MirrorMaker2
dlq:                model.feedback.dlq
```

**Avro Schema:**
```json
{
  "type": "record",
  "name": "ModelFeedback",
  "namespace": "io.ras.ml.v1",
  "fields": [
    {"name": "request_id",     "type": "string"},
    {"name": "customer_id",    "type": "string"},
    {"name": "original_score", "type": "int"},
    {"name": "original_decision","type": "string"},
    {"name": "outcome",        "type": {"type": "enum", "name": "Outcome",
                                "symbols": ["true_positive","false_positive",
                                            "true_negative","false_negative"]}},
    {"name": "source",         "type": {"type": "enum", "name": "FeedbackSource",
                                "symbols": ["analyst_resolution","chargeback",
                                            "merchant_api","law_enforcement"]}},
    {"name": "model_version",  "type": "string"},
    {"name": "submitted_by",   "type": "string"},
    {"name": "occurred_at",    "type": {"type": "long",
                                "logicalType": "timestamp-millis"}}
  ]
}
```

**@yuki:** "This topic is the ground truth pipeline for model retraining. Every `false_positive` label from analyst resolution tells me the model over-scored a legitimate transaction. Accumulated over 30 days, these labels form the retraining dataset supplement — I backfill them into Snowflake weekly via the PySpark pipeline. The `source` field lets me weight labels differently: analyst resolution labels are high-confidence; chargeback labels are medium-confidence (chargebacks can be friendly fraud)."

---

### 3.6 `audit.log`

**Purpose:** Secondary audit event stream for compliance tooling. Mirrors the Cassandra immutable event log for downstream compliance consumers (Elasticsearch indexing, Snowflake cold storage, SIEM integration).

```yaml
topic:              audit.log
partitions:         24
replication_factor: 3
retention:          7 days (Kafka) → Snowflake sink (7 years — AML compliance)
cleanup_policy:     delete
partition_key:      customer_id
compression:        lz4
producers:          ras-scoring-api
                    ras-case-service
                    ras-admin-api
consumers:          elasticsearch-sink    (audit search index)
                    snowflake-sink        (7-year cold storage)
                    siem-connector        (security event monitoring)
cross_region:       replicated via MirrorMaker2
dlq:                audit.log.dlq
```

**@james:** "This topic is the compliance distribution bus. The Elasticsearch sink builds the searchable audit index used by analysts for GDPR data subject access requests. The Snowflake sink provides the 7-year retention required by the Bank Secrecy Act for AML record-keeping — Kafka's 7-day retention is just the transit buffer. The SIEM connector feeds our security information and event management platform for real-time anomaly detection."

**@priya:** "All messages on `audit.log` undergo PII field-level encryption before publish — same KMS envelope encryption as the database (ADR-003). The Elasticsearch and Snowflake sinks have the KMS decrypt permission scoped to their IAM roles. The SIEM connector receives pseudonymised data only — it does not need PII to detect security anomalies."

---

### 3.7 Dead Letter Queue (DLQ) Topics

Every consumer topic has a corresponding DLQ. Messages are routed to the DLQ after `max.poll.retries` (default: 3) failed processing attempts.

```yaml
dlq_topics:
  - risk.decisions.dlq
  - risk.events.dlq
  - cases.created.dlq
  - rules.changed.dlq
  - model.feedback.dlq
  - audit.log.dlq

dlq_config:
  partitions:         3          # Lower throughput — failure path
  replication_factor: 3
  retention:          7 days     # Time for ops team to investigate + replay
  cleanup_policy:     delete

dlq_schema:           # Wraps original message with failure metadata
  original_topic:     string
  original_partition: int
  original_offset:    long
  original_payload:   bytes      # Original Avro message, verbatim
  error_message:      string
  error_class:        string
  failed_at:          timestamp-millis
  retry_count:        int
  consumer_group:     string
```

**DLQ Monitoring (@darius):**
```
Alert: kafka_dlq_messages_total{topic=~".*dlq"} > 0
Severity: P2
Runbook: docs/runbooks/kafka_consumer_lag.md
On-call: @darius (infrastructure) + owning service team
```

**DLQ Replay:**
```bash
# Replay DLQ messages back to original topic after root cause fix
kafka-consumer-groups --bootstrap-server $KAFKA_BROKERS \
  --group ras-dlq-replayer \
  --topic risk.decisions.dlq \
  --reset-offsets --to-earliest --execute

# DLQ replayer consumer group reads from DLQ,
# re-publishes to original topic with original key/value
```

---

## 4. Consumer Groups

| Consumer Group | Topic(s) Consumed | Service | Lag Alert |
|---|---|---|---|
| `ras-scoring-decisions` | `risk.decisions` | Flink pipeline | > 2,000 msgs |
| `ras-case-trigger` | `cases.created` | Case service | > 500 msgs |
| `ras-rule-cache` | `rules.changed` | Scoring API (all pods) | > 10 msgs |
| `ras-ml-label-collector` | `model.feedback` | ML training pipeline | > 5,000 msgs |
| `ras-audit-elastic` | `audit.log` | Elasticsearch sink | > 10,000 msgs |
| `ras-audit-snowflake` | `audit.log` | Snowflake sink | > 50,000 msgs |
| `ras-model-monitor` | `risk.events` | Evidently AI connector | > 10,000 msgs |
| `ras-sla-monitor` | `cases.created` | SLA tracking service | > 100 msgs |

---

## 5. Flink Topology

Apache Flink consumes `risk.decisions` and `risk.events` to compute real-time features that are written back to Feast (Redis online store).

```
risk.decisions (Kafka)
        │
        ▼
┌───────────────────────────────────────────────────────┐
│                  Flink Job: feature-aggregator         │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Operator 1: Velocity Window Aggregation        │  │
│  │                                                 │  │
│  │  KeyBy: customer_id                             │  │
│  │  Windows:                                       │  │
│  │    ProcessingTimeWindow(60s)  → txn_count_60s   │  │
│  │    ProcessingTimeWindow(1h)   → txn_amount_1h   │  │
│  │    ProcessingTimeWindow(24h)  → txn_declined_24h│  │
│  │    ProcessingTimeWindow(24h)  → distinct_merch  │  │
│  │  Watermark: 5s allowed lateness                 │  │
│  └─────────────────────────────────────────────────┘  │
│                          │                            │
│                          ▼                            │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Operator 2: Graph Feature Trigger              │  │
│  │                                                 │  │
│  │  On new customer_id seen:                       │  │
│  │    Query Neo4j (async):                         │  │
│  │      linked_fraud_ring_score                    │  │
│  │      device_account_count_7d                    │  │
│  │      shared_device_accounts                     │  │
│  │  Timeout: 200ms (fail open → stale value)       │  │
│  └─────────────────────────────────────────────────┘  │
│                          │                            │
│                          ▼                            │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Sink: Feast Online Store (Redis)               │  │
│  │                                                 │  │
│  │  HSET feast:{customer_id} {feature: value, ...} │  │
│  │  EXPIRE feast:{customer_id} 86400  (24h TTL)    │  │
│  └─────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

**Flink Checkpointing:**
```yaml
checkpoint_interval:   30s
checkpoint_mode:       EXACTLY_ONCE
state_backend:         RocksDB (persistent, survives pod restart)
checkpoint_storage:    s3://ras-flink-checkpoints/
min_pause_between:     10s
```

**@marcus:** "Flink EXACTLY_ONCE semantics with RocksDB state backend means: if a Flink pod crashes mid-window computation, it restores from the last checkpoint and reprocesses from the saved Kafka offset. No velocity feature is lost or double-counted. The 30-second checkpoint interval is the maximum window of re-processing on recovery — acceptable given our 60-second velocity windows."

---

## 6. Producer Configuration

All RAS Kafka producers use the following base configuration:

```python
# app/core/kafka_producer.py

from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

PRODUCER_CONFIG = {
    # Connection
    "bootstrap.servers":        os.environ["KAFKA_BROKERS"],
    "security.protocol":        "SASL_SSL",
    "sasl.mechanism":           "PLAIN",
    "sasl.username":            vault.get("kafka/producer/username"),
    "sasl.password":            vault.get("kafka/producer/password"),

    # Reliability
    "acks":                     "all",          # All ISR replicas must ack
    "retries":                  10,
    "retry.backoff.ms":         100,
    "delivery.timeout.ms":      5000,           # 5s max delivery time
    "enable.idempotence":       True,           # Exactly-once delivery

    # Performance
    "linger.ms":                5,              # Batch for 5ms
    "batch.size":               65536,          # 64KB batch
    "compression.type":         "lz4",

    # Schema Registry
    "schema.registry.url":      os.environ["SCHEMA_REGISTRY_URL"],
}
```

**`enable.idempotence = True`** prevents duplicate messages on producer retry — if a network timeout causes the producer to retry a send, the broker deduplicates using the producer sequence number. Combined with `acks=all`, this gives exactly-once producer semantics.

---

## 7. Consumer Configuration

```python
# app/core/kafka_consumer.py

CONSUMER_CONFIG = {
    # Connection
    "bootstrap.servers":        os.environ["KAFKA_BROKERS"],
    "security.protocol":        "SASL_SSL",
    "sasl.mechanism":           "PLAIN",
    "sasl.username":            vault.get("kafka/consumer/username"),
    "sasl.password":            vault.get("kafka/consumer/password"),

    # Consumer group
    "group.id":                 os.environ["KAFKA_CONSUMER_GROUP"],
    "auto.offset.reset":        "earliest",     # New group starts from beginning
    "enable.auto.commit":       False,          # Manual commit — idempotent processing

    # Reliability
    "max.poll.interval.ms":     300000,         # 5 min max processing time per batch
    "session.timeout.ms":       30000,
    "heartbeat.interval.ms":    3000,

    # Performance
    "fetch.min.bytes":          1024,
    "fetch.max.wait.ms":        500,
}

# Manual offset commit pattern (idempotent consumer):
async def consume_and_process(consumer, handler):
    msg = consumer.poll(timeout=1.0)
    if msg is None or msg.error():
        return
    try:
        await handler(msg)               # Process message
        consumer.commit(msg)             # Commit only after successful processing
    except Exception as e:
        await route_to_dlq(msg, e)       # DLQ on failure
        consumer.commit(msg)             # Commit to avoid infinite retry
```

**`enable.auto.commit = False`** ensures offsets are committed only after successful processing. If the consumer crashes after processing but before commit, the message is re-delivered — which is why all consumers must be idempotent (K4).

---

## 8. Topic Monitoring

### 8.1 Key Metrics (Prometheus + Confluent Metrics API)

| Metric | Alert Threshold | Severity |
|---|---|---|
| `kafka_consumer_lag{group, topic}` | > 2,000 (risk.decisions) | P2 |
| `kafka_consumer_lag{group, topic}` | > 100 (rules.changed) | P1 |
| `kafka_consumer_lag{group, topic}` | > 0 (*.dlq) | P2 |
| `kafka_producer_error_rate` | > 0.1% | P2 |
| `kafka_under_replicated_partitions` | > 0 | P1 |
| `kafka_offline_partitions` | > 0 | P1 |
| `kafka_broker_count` | < 9 | P1 |
| `kafka_mirrormaker_replication_lag` | > 10,000 msgs | P2 |

### 8.2 Grafana Dashboard

Dashboard: `https://grafana.ras.internal/d/kafka-overview`

Panels:
- Consumer lag per group (all topics)
- Producer throughput (msgs/sec, bytes/sec)
- End-to-end latency (produce → consume)
- DLQ depth per topic
- MirrorMaker2 replication lag (cross-region)
- Broker disk utilisation per AZ

---

## 9. Topic Governance

### 9.1 Topic Creation Policy

New topics require:
1. **ADR or design doc** — document the purpose, consumers, schema, and retention
2. **Avro schema** — registered in Schema Registry before first message
3. **DLQ topic** — created alongside the main topic
4. **Consumer group** — registered in monitoring before deployment
5. **@marcus approval** — Architecture Review Board sign-off

```bash
# Topic creation script (Terraform-managed — not manual)
# terraform/kafka/topics.tf

resource "confluent_kafka_topic" "risk_decisions" {
  kafka_cluster { id = var.kafka_cluster_id }
  topic_name    = "risk.decisions"
  partitions_count = 24
  config = {
    "retention.ms"       = "604800000"  # 7 days
    "cleanup.policy"     = "delete"
    "compression.type"   = "lz4"
    "min.insync.replicas"= "2"
  }
}
```

### 9.2 Schema Evolution Policy

| Change Type | Compatibility | Process |
|---|---|---|
| Add optional field (`default` provided) | BACKWARD ✅ | PR + Schema Registry update |
| Add required field (no default) | BREAKING ❌ | New topic version + migration plan |
| Remove field | BACKWARD ⚠️ | Deprecate first, remove after all consumers updated |
| Rename field | BREAKING ❌ | New topic version + migration plan |
| Change field type | BREAKING ❌ | New topic version + migration plan |

---

## 10. Related Documents

| Document | Location | Owner |
|---|---|---|
| System Architecture Overview | `docs/architecture/system_overview.md` | `@marcus` |
| ADR-002 (Cassandra event log) | `docs/architecture/adr/ADR-002-cassandra-event-log.md` | `@marcus` |
| ADR-006 (Redis velocity) | `docs/architecture/adr/ADR-006-redis-velocity-counters.md` | `@marcus` |
| ADR-008 (Kafka rule distribution) | `docs/architecture/adr/ADR-008-kafka-rule-distribution.md` | `@marcus` |
| Kafka Consumer Lag Runbook | `docs/runbooks/kafka_consumer_lag.md` | `@darius` |
| ML Pipeline Architecture | `docs/ml/pipeline_architecture.md` | `@yuki` |
| Audit Log Compliance | `docs/compliance/pci_dss_controls.md` | `@james` |

---

*Document Version: 1.0.0*
*Owner: Marcus Chen — Chief Risk Architect*
*Review Cycle: Per sprint (schema changes) · Quarterly (topology review)*
*Classification: Internal — Engineering Confidential*