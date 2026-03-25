# Sprint 1 — Backend Core

**Goal:** A transaction can be scored end-to-end (rule-only, no ML yet).

**Duration:** 2 weeks  
**Lead:** `@sofia`  
**Supporting:** `@marcus`, `@aisha`

---

## Scoring API

`@sofia` leads

```
[ ] POST /v1/risk/score endpoint
[ ] RiskScoreRequest + RiskDecision Pydantic schemas
[ ] Idempotency key middleware (Redis)
[ ] Request validation — all fields, all edge cases
[ ] Response serialization
```

---

## Database Layer

`@sofia` leads

```
[ ] risk_decisions table + Alembic migration
[ ] cases table + migration
[ ] rules table + migration
[ ] SQLAlchemy async repositories
[ ] PgBouncer connection pooling configured
[ ] Read replica routing for analytics queries
```

---

## Kafka Integration

`@sofia` leads

```
[ ] Confluent Kafka producer (risk.decisions topic)
[ ] Schema Registry — RiskDecision Avro schema registered
[ ] Async publish (non-blocking — decision returned to client first)
```

---

## Cassandra Integration

`@sofia` leads

```
[ ] risk.events table created (INSERT-only service account)
[ ] Async write to audit log
[ ] DLQ buffering on write failure
```

---

## Architecture Review

`@marcus` reviews

```
[ ] ADR compliance — Cassandra for event log (ADR-002)
[ ] Kafka topic naming + partition strategy matches kafka_topics.md
[ ] Service boundaries respected
```

---

## Testing

`@aisha` writes

```
[ ] Unit tests — scoring schemas, validation, idempotency
[ ] Integration tests — DB writes, Kafka publish, Cassandra write
[ ] Contract tests — scoring API provider (Pact)
[ ] Target: 85% coverage on new code
```

---

## Completion Criteria

✅ Sprint 1 done when:
- POST /v1/risk/score returns a decision
- Decision is written to PostgreSQL + Cassandra + Kafka
- All tests pass

---

**Owner:** Sofia Martínez (`@sofia`)  
**Status:** ⏳ Not started  
**Created:** 2026-03-25
