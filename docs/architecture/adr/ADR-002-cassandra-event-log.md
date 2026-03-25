# ADR-002: Event Log Storage — Cassandra over PostgreSQL

```yaml
id:         ADR-002
title:      Immutable Event Log Storage Engine
status:     Accepted
date:       2024-01-08  (Pre-development)
author:     Marcus Chen (@marcus)
reviewers:  "@sofia · @darius · @james"
deciders:   "@marcus"
supersedes: —
superseded_by: —
```

## Context

RAS must maintain an immutable, append-only audit log of every scoring decision. Requirements:

- **Write throughput:** 50,000+ writes/second at production peak (100k TPS scoring × 0.5 audit events per transaction)
- **Retention:** 90 days hot (PCI DSS Req 10.5.1 minimum), 7 years cold (AML compliance)
- **Immutability:** No UPDATE or DELETE operations — audit integrity requirement (PCI DSS Req 10.3.2)
- **Read pattern:** Time-ordered reads per customer ID (analyst investigation, model feature backfill)
- **Multi-region:** Active-active replication across 3 regions (RPO < 1 second)
- **Availability:** 99.99% write availability

Candidates: **Apache Cassandra 5**, **PostgreSQL 16**, **Amazon DynamoDB**, **Apache Kafka (as store)**

## Decision

**Use Apache Cassandra 5 as the immutable event log store.**

Schema:
```cql
CREATE TABLE risk.events (
    customer_id   TEXT,
    occurred_at   TIMEUUID,
    event_type    TEXT,
    payload       TEXT,       -- JSON, field-encrypted PII
    PRIMARY KEY ((customer_id), occurred_at)
) WITH CLUSTERING ORDER BY (occurred_at DESC)
  AND default_time_to_live = 7776000   -- 90 days
  AND gc_grace_seconds = 86400;
```

Consistency: `LOCAL_QUORUM` for writes, `LOCAL_ONE` for reads.

## Rationale

**Why not PostgreSQL:**

At Stripe's risk infrastructure (pre-2019), a PostgreSQL append-only audit table at 20k TPS write throughput experienced VACUUM contention within 6 months — MVCC dead tuple accumulation outpaced autovacuum's ability to reclaim space. At 50k TPS with 90-day retention, the `risk_decisions` table would accumulate ~130 billion rows annually. PostgreSQL's B-tree index maintenance and MVCC overhead become pathological at this scale.

Specific failure modes observed:
- `autovacuum` cannot keep pace → table bloat → sequential scan fallback → P99 latency degradation
- Write amplification on B-tree index updates → IOPS exhaustion
- WAL volume at 50k TPS → replication lag on read replicas

**Why Cassandra:**

Cassandra's LSM-tree (Log-Structured Merge-tree) storage engine is architecturally optimised for write-heavy, append-only workloads. Writes go to a memtable (in-memory) and WAL (commit log), flushed to SSTables periodically. There are no index maintenance overheads on write. Compaction (Cassandra's equivalent of VACUUM) runs asynchronously and does not block writes.

The `(customer_id, occurred_at TIMEUUID)` primary key gives:
- Partition by customer: all events for a customer are co-located → analyst investigation reads are single-partition
- Clustering by time: time-ordered reads within a partition are sequential → sub-5ms P99
- TIMEUUID for `occurred_at`: monotonic, globally unique, no clock skew collisions

`default_time_to_live = 7776000` (90 days) implements the PCI DSS Req 10.5.1 hot retention automatically — no deletion job required, no VACUUM equivalent needed.

**Multi-DC replication:**
Cassandra's `NetworkTopologyStrategy` with `RF=3` per DC gives active-active multi-region replication natively. Postgres logical replication requires a primary — Cassandra has no primary.

## Consequences

**Positive:**
- Sub-5ms P99 write latency at 50k TPS, sustained indefinitely
- TTL-based retention — zero operational overhead for expiry
- Multi-DC active-active — no primary election on regional failure
- Immutability enforced at service account privilege level (INSERT only)

**Negative:**
- No JOINs, no ACID transactions across tables — Cassandra is not a relational store
- Schema design requires upfront access pattern analysis — cannot add ad-hoc queries
- Operational complexity vs. PostgreSQL — requires Cassandra expertise (@darius)
- Eventual consistency model — `LOCAL_QUORUM` mitigates but does not eliminate

**Constraints imposed:**
- Cassandra is NEVER queried with JOINs — all relational queries go to PostgreSQL
- All analytical queries go to Snowflake (cold path) — not Cassandra
- Read access is per-customer-partition only — no full table scans in production

*ADR Directory Version: 1.0.0*
*Owner: Marcus Chen — Chief Risk Architect*
*Format: MADR (Markdown Architectural Decision Records)*
*Review: New ADRs require Architecture Review Board approval*
*Classification: Internal — Engineering Confidential*