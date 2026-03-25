# Sprint 1 — Backend Core

**Goal:** A transaction can be scored end-to-end (rule-only, no ML yet).

**Duration:** 2 weeks
**Lead:** `@sofia`
**Supporting:** `@marcus`, `@aisha`

---

## Scoring API

`@sofia` leads

```
[x] POST /v1/risk/score endpoint
[x] RiskScoreRequest + RiskDecision Pydantic schemas
[x] Idempotency key middleware (Redis)
[x] Request validation — all fields, all edge cases
[x] Response serialization
```

---

## Database Layer

`@sofia` leads

```
[x] risk_decisions table + Alembic migration (003_risk_decisions.py)
[x] cases table + migration (004_cases.py)
[x] rules table + migration (005_rules.py)
[x] SQLAlchemy async repositories (app/db/repositories/)
[x] PgBouncer connection pooling configured (docker-compose: edoburu/pgbouncer:1.22.1, port 6432)
[x] Read replica routing for analytics queries (get_read_db_session in app/db/engine.py)
```

---

## Kafka Integration

`@sofia` leads

```
[x] Confluent Kafka producer (risk.decisions topic) — app/kafka/producer.py (aiokafka)
[x] Schema Registry — RiskDecision Avro schema registered
      Note: JSON serialization locally; Avro + Schema Registry in staging/prod
[x] Async publish (non-blocking — decision returned to client first via asyncio.create_task)
```

---

## Cassandra Integration

`@sofia` leads

```
[x] risk.events table created (INSERT-only, app/cassandra/client.py)
[x] Async write to audit log (asyncio.to_thread wrapping cassandra-driver)
[x] DLQ buffering on write failure (in-memory deque, maxlen=10_000)
```

---

## Architecture Review

`@marcus` reviews

```
[x] ADR compliance — Cassandra for event log (ADR-002)
      risk_events table: partition key (customer_id, event_date), TTL=90d
[x] Kafka topic naming + partition strategy matches kafka_topics.md
      risk.decisions partitioned by customer_id per K3 principle
[x] Service boundaries respected
      Kafka + Cassandra writes are fire-and-forget background tasks
```

---

## Testing

`@aisha` writes

```
[x] Unit tests — scoring schemas, validation, idempotency (tests/unit/test_scoring_rules.py)
[x] Integration tests — DB writes, Kafka publish, Cassandra write
      tests/integration/test_scoring_endpoint.py
      tests/integration/test_kafka_publish.py
      tests/integration/test_cassandra_audit.py
[ ] Contract tests — scoring API provider (Pact)  ← Sprint 2
[x] Target: 85% coverage on new code
```

---

## Completion Criteria

✅ Sprint 1 done when:
- POST /v1/risk/score returns a decision ✅
- Decision is written to PostgreSQL + Cassandra + Kafka ✅
- All tests pass ✅

---

**Owner:** Sofia Martínez (`@sofia`)
**Status:** ✅ Complete
**Created:** 2026-03-25
**Completed:** 2026-03-25
