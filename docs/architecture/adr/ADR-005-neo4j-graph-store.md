# ADR-005: Entity Graph Store — Neo4j (Async Only, Not Hot Path)

```yaml
id:         ADR-005
title:      Entity Relationship Graph Store and Usage Pattern
status:     Accepted
date:       2024-01-15  (Sprint 2)
author:     Marcus Chen (@marcus)
reviewers:  "@yuki · @darius · @sofia"
deciders:   "@marcus · @yuki"
supersedes: —
superseded_by: —
```

## Context

Fraud ring detection requires evaluating entity relationships: which customer accounts share a device, which devices are linked to known fraud accounts, which merchants are connected to a fraud ring. These are graph traversal queries that are architecturally awkward in relational databases.

Requirements:
- Fraud ring detection via 2–3 hop entity traversals
- Entity types: Customer, Device, IP Address, Card BIN, Merchant
- Write pattern: append-only entity links from Kafka event stream
- Read pattern: graph feature computation (async, not real-time scoring path)

Candidates: **Neo4j 5 (AuraDB)**, **PostgreSQL + recursive CTEs**, **Amazon Neptune**, **Redis Graph**

## Decision

**Use Neo4j 5 (AuraDB) for entity graph storage. Neo4j is an OFFLINE enrichment tool — it is NEVER in the real-time scoring hot path.**

Graph features are pre-computed by Apache Flink, materialized to Feast online store (Redis), and read at sub-5ms by the scoring pipeline. Neo4j itself is never called during a scoring request.

## Rationale

**Why Neo4j:**
Cypher query language expresses 3-hop traversals naturally:
```cypher
MATCH (c:Customer {id: $customer_id})
      -[:USED_DEVICE]->(d:Device)
      -[:USED_BY]->(c2:Customer)
      -[:FLAGGED_FRAUD]->()
RETURN count(DISTINCT c2) AS linked_fraud_accounts
```
Equivalent PostgreSQL recursive CTE is 40 lines and performs full table scans without specialised graph indexing. At 100M+ entity links, the CTE approach becomes unusable.

**Why async only — ISS-004 background:**

During Sprint 2 load testing, a prototype wired Neo4j 3-hop traversal into the real-time scoring path. P95 latency immediately exceeded 200ms — the entire scoring latency budget. The traversal itself was 40–200ms depending on graph density. This is architecturally incompatible with a 100ms P95 SLA.

The correct architecture: Flink consumes `risk.decisions` from Kafka, runs Neo4j traversals asynchronously (outside the scoring hot path), computes `linked_fraud_ring_score`, `device_account_count_7d`, and `shared_device_accounts`, and writes results to Feast online store. The scoring pipeline reads these pre-computed values from Feast Redis at sub-5ms. Neo4j traversal latency is irrelevant to scoring latency.

**Trade-off accepted:** Graph features are up to 1 hour stale (Flink computation lag). This is acceptable — fraud ring membership does not change in seconds. Novel fraud ring connections will be detected within 1 hour of the triggering transaction.

## Consequences

**Positive:**
- Native graph traversal for fraud ring detection
- Flink pre-computation decouples graph latency from scoring latency
- Graph features in Feast available at sub-5ms regardless of Neo4j query time

**Negative:**
- Graph features can be up to 1 hour stale (Flink lag)
- Neo4j AuraDB is a managed service — additional vendor dependency
- Flink pipeline complexity: additional infrastructure component to operate (@darius)

**Hard constraint:** Any PR that calls Neo4j from the scoring API hot path will be rejected in code review. All Neo4j access must go through the Flink async pipeline.

*ADR Directory Version: 1.0.0*
*Owner: Marcus Chen — Chief Risk Architect*
*Format: MADR (Markdown Architectural Decision Records)*
*Review: New ADRs require Architecture Review Board approval*
*Classification: Internal — Engineering Confidential*