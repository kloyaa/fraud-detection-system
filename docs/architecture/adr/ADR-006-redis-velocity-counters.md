# ADR-006: Velocity Counter Implementation — Redis Sorted-Set Sliding Window

```yaml
id:         ADR-006
title:      Real-Time Velocity Counter Implementation
status:     Accepted
date:       2024-01-15  (Sprint 2)
author:     Marcus Chen (@marcus)
reviewers:  "@sofia · @darius · @yuki"
deciders:   "@marcus · @sofia"
supersedes: —
superseded_by: —
```

## Context

Velocity checks (transactions per customer in last 60 seconds, total amount in last hour, etc.) are among the highest-signal fraud features. They must be computed on every scoring request with sub-millisecond latency, atomically, and without race conditions.

Requirements:
- Sub-1ms computation latency (Redis in-memory)
- Atomic increment + count in a single round-trip
- True sliding window (not fixed tumbling window)
- 6 velocity dimensions: customer × 60s, customer × 1h, merchant × 60s, device × 5min, IP × 60s, amount × 1h
- Horizontal scale — must work across 20+ scoring API pods simultaneously

Candidates: **Redis sorted-set sliding window**, **Kafka Streams tumbling window**, **Flink sliding window**, **PostgreSQL counter table**

## Decision

**Use Redis sorted-set sliding window per velocity dimension, executed in a Lua script pipeline.**

```python
# Atomic pipeline per velocity dimension (no round-trip overhead):
ZADD  vel:{entity}:{window}  {now}  {txn_id}     # Add current event
ZREMRANGEBYSCORE vel:{entity}:{window} 0 {cutoff} # Remove expired
ZCARD vel:{entity}:{window}                        # Count in window
EXPIRE vel:{entity}:{window} {window + 1}          # TTL cleanup
```

All four commands execute atomically in a single Redis pipeline. Result: current event count in the sliding window returned in ~0.3ms.

## Rationale

**Why not Kafka Streams:**
Kafka Streams windows are tumbling or hopping — a 60-second tumbling window resets at :00, :60, :120. A fraud attempt that spans two windows (30 transactions at :45, 30 transactions at :15 of the next window) is invisible to a tumbling window but visible to a true sliding window. Sliding windows require stateful stream processing and have minimum 500ms latency due to watermark computation.

**Why not Flink:**
Flink is used for graph feature aggregation (multi-second windows with complex join logic). For 60-second velocity counters where sub-millisecond latency is required, Flink's overhead is inappropriate. Flink is the right tool for the Feast feature pipeline; Redis is the right tool for hot-path velocity checks.

**Why not PostgreSQL:**
An `UPDATE counter SET value = value + 1` at 100k TPS across 6 dimensions = 600k writes/second to a single PostgreSQL table. Row-level locking under this write pattern causes lock contention and latency spikes. PostgreSQL is not designed for this access pattern.

**Redis sorted-set correctness:**
The sorted-set approach is a true sliding window because: the score is the event timestamp (float unix seconds), `ZREMRANGEBYSCORE` removes all events older than `now - window_seconds`, and `ZCARD` counts only events within the window. No rounding, no bucketing, no edge effects.

**Atomicity across 20 pods:**
Redis sorted-set operations are atomic at the Redis server level — ZADD and ZCARD see consistent state regardless of how many application pods are writing concurrently. The pipeline (ZADD + ZREMRANGEBYSCORE + ZCARD + EXPIRE) executes as a single atomic unit via Lua script, preventing TOCTOU race conditions.

## Consequences

**Positive:**
- Sub-millisecond velocity computation in hot path
- True sliding window — no false negatives at window boundaries
- Atomic across all scoring pods — no race conditions
- TTL-based cleanup — zero operational overhead

**Negative:**
- Redis Cluster required (6 velocity dimensions × 100k customers = ~600k active keys) — @darius owns cluster sizing
- Redis unavailability → velocity checks must fail open (degraded mode documented in system_overview.md §10)
- Memory sizing: each velocity key ≈ 200 bytes × 100k active customers × 6 dimensions ≈ 120 MB — well within Redis Cluster capacity

*ADR Directory Version: 1.0.0*
*Owner: Marcus Chen — Chief Risk Architect*
*Format: MADR (Markdown Architectural Decision Records)*
*Review: New ADRs require Architecture Review Board approval*
*Classification: Internal — Engineering Confidential*