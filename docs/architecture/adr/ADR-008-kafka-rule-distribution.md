# ADR-008: Rule Distribution — Kafka-Based Refresh over Redis Cache TTL

```yaml
id:             ADR-008
title:          Rule Engine Configuration Distribution Strategy
status:         Accepted
date:           2024-03-18  (Pre-development)
author:         Marcus Chen (@marcus)
reviewers:      "@sofia · @darius · @priya · @james"
deciders:       "@marcus · @sofia"
supersedes:     —
superseded_by:  —
linked_issues:  ISS-006 (rule propagation latency)
linked_adr:     ADR-002 (Cassandra audit trail) · ADR-006 (Redis cluster topology)
```

## Context

The rule engine in each scoring API pod maintains an in-process cache of active rule definitions (loaded from PostgreSQL at startup). When a risk analyst updates a rule via the Admin API, all scoring pods must refresh their cache. The question is: what is the rule distribution mechanism?

Requirements:
- Rule changes must propagate to all scoring pods within < 5 seconds
- No pod restart required on rule change
- Ordering guarantee: all pods must apply the same rule version in the same sequence
- At-least-once delivery: a pod that restarts mid-distribution must catch up on missed changes
- Auditable: every rule change logged with author identity, timestamp, and version
- Rollback: a bad rule must be reversible without a deployment

Candidates: **Kafka topic (rules.changed)**, **Redis pub/sub**, **Redis key with TTL polling**, **Admin API push to all pods**

## Decision

**Use Kafka `rules.changed` topic (single partition) for rule change distribution. Each scoring pod is a consumer group member and refreshes its in-process rule cache on message receipt. Rule cache refresh is synchronous — the pod commits the Kafka offset only after the PostgreSQL re-read completes successfully.**

```
Admin API
  │
  ├─► PostgreSQL: INSERT rule (version N) — source of truth
  │     (committed before Kafka publish)
  │
  └─► Kafka rules.changed (single partition):
        { rule_id, version: N, action, changed_by, occurred_at }
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
      Pod 1      Pod 2      Pod N
  (consumer)  (consumer)  (consumer)
      │            │           │
      ▼            ▼           ▼
  Re-read      Re-read     Re-read
  rule from    rule from   rule from
  PostgreSQL   PostgreSQL  PostgreSQL
  (version N)  (version N) (version N)
      │
      ▼
  Commit Kafka offset
  (only after DB read succeeds)
```

## Resolution of Pre-development Open Questions

### Q1: Synchronous or async rule refresh?

**Decision: Synchronous.**

The pod re-reads the rule from PostgreSQL and updates its in-process cache before committing the Kafka offset. If the PostgreSQL read fails, the offset is not committed — the pod will re-consume the message on the next poll and retry. This guarantees the pod never acknowledges a rule change it has not applied.

Async (ack-then-refresh) was rejected because it creates a window where the pod has committed the offset but has not yet applied the rule — if the pod crashes in that window, the rule change is silently lost for that pod until the next rule change or pod restart.

*@sofia:* "Synchronous refresh adds ~3ms per rule change event (one PostgreSQL read). Rule changes are rare — a few per day at most. The latency cost is negligible and the correctness guarantee is non-negotiable."

### Q2: Race condition — new pod starts between Kafka publish and PostgreSQL commit?

**Decision: PostgreSQL commit always precedes Kafka publish. Readiness probe gates traffic.**

The Admin API executes in this strict order:
1. `BEGIN` PostgreSQL transaction
2. `INSERT INTO rules (rule_id, version, ...)` — write rule
3. `COMMIT` — rule is durable in PostgreSQL
4. Publish to Kafka `rules.changed` — pointer only, no payload

A new pod starting between steps 3 and 4 will: (a) load all existing rules from PostgreSQL at startup (step 3 is committed — rule is visible), and (b) consume the Kafka message when it arrives and attempt a re-read — which is a no-op since the rule is already in cache at the correct version.

A new pod starting before step 3 will load rules without the new version, then receive the Kafka message and re-read — updating to the correct version. No divergence possible.

The readiness probe does not pass until the pod has consumed all `rules.changed` messages up to the current offset — ensuring the pod enters the load balancer with a fully current rule cache.

*@marcus:* "PostgreSQL-first, Kafka-second is the invariant. Kafka is a notification bus, not a data store. PostgreSQL is the authoritative rule store. The Kafka message is a pointer — `{rule_id, version}` — not the rule itself. This means even if a Kafka message is delivered twice (at-least-once), the idempotent PostgreSQL read produces the same result."

### Q3: Rollback strategy for a bad rule?

**Decision: Rule versioning with explicit `disable` action. No Kafka message deletion.**

Every rule has a version counter in PostgreSQL. A rollback is implemented as a new rule change event — not a deletion or Kafka message retraction:

```python
# Admin API — rollback a bad rule to previous version
async def rollback_rule(rule_id: str, target_version: int, changed_by: str):
    async with db.begin():
        # Write previous version as new current version (version N+1)
        await db.execute("""
            INSERT INTO rules (rule_id, version, definition, is_active, changed_by)
            SELECT rule_id, :new_version, definition, is_active, :changed_by
            FROM rules
            WHERE rule_id = :rule_id AND version = :target_version
        """, {
            "rule_id": rule_id,
            "new_version": await _next_version(rule_id),
            "target_version": target_version,
            "changed_by": changed_by,
        })

    # Publish rollback event — same mechanism as any rule change
    await kafka_producer.send("rules.changed", {
        "rule_id":    rule_id,
        "version":    new_version,
        "action":     "rollback",
        "rolled_back_to": target_version,
        "changed_by": changed_by,
        "occurred_at": utcnow(),
    })
```

Rollback propagates to all pods via the same Kafka mechanism as any rule change — < 500ms. The audit trail in Cassandra records both the bad rule deployment and the rollback event with full identity and timestamp.

*@james:* "The versioned rollback approach satisfies PCI DSS Requirement 6.3.3 — all system components are protected from known vulnerabilities — and creates a complete, non-repudiable audit trail of who deployed a bad rule and who rolled it back. A hard delete from Kafka would destroy audit evidence. This approach preserves it."

## Rationale (Summary)

**Why not Redis TTL polling:**
60-second TTL → up to 60-second stale rule window. A new `BLOCK` rule for a confirmed fraud device would not fire for up to 60 seconds — unacceptable. Requirement is < 5 seconds.

**Why not Redis pub/sub:**
No persistence. A pod restarting during a pub/sub message misses it permanently — rule cache diverges silently from the fleet. Kafka consumer group offsets provide at-least-once delivery regardless of pod lifecycle.

**Why not Admin API push:**
Requires service discovery of all pod IPs, retry logic for pods starting up, and coupling between Admin API and scoring API deployment topology. Operationally fragile.

**Why Kafka (single partition):**
Single partition = total ordering. All pods apply rule changes in the same sequence. At-least-once delivery. PostgreSQL remains the authoritative store — Kafka is a notification bus only. Propagation latency < 500ms (Kafka < 100ms + PostgreSQL re-read < 200ms + cache update < 5ms).

## Implementation (Pre-development)

```python
# app/engines/rule_cache.py

import asyncio
from confluent_kafka import Consumer
from app.repositories.rules import RuleRepository
import structlog

log = structlog.get_logger()

class RuleCacheRefresher:
    """
    Kafka consumer that keeps the in-process rule cache
    synchronised with PostgreSQL rule definitions.

    Runs as a background asyncio task in each scoring API pod.
    Offset committed only after successful PostgreSQL re-read.
    """

    def __init__(
        self,
        consumer: Consumer,
        rule_repo: RuleRepository,
        rule_cache: dict,          # Shared in-process cache
    ):
        self.consumer   = consumer
        self.rule_repo  = rule_repo
        self.cache      = rule_cache
        self._ready     = asyncio.Event()

    async def start(self) -> None:
        """
        On startup: load all rules from PostgreSQL, then
        consume Kafka backlog to catch any changes that
        occurred during pod restart.
        """
        # Step 1: Full load from PostgreSQL (source of truth)
        rules = await self.rule_repo.get_all_active()
        self.cache.update({r.rule_id: r for r in rules})
        log.info("rule_cache_loaded", count=len(rules))

        # Step 2: Consume Kafka backlog to current offset
        await self._consume_to_current_offset()

        # Step 3: Signal readiness (readiness probe checks this)
        self._ready.set()
        log.info("rule_cache_ready")

        # Step 4: Continuous consumption
        await self._consume_loop()

    async def _consume_loop(self) -> None:
        while True:
            msg = self.consumer.poll(timeout=1.0)
            if msg is None or msg.error():
                continue
            try:
                event = RuleChangedEvent.parse(msg.value())
                # Synchronous re-read from PostgreSQL
                rule = await self.rule_repo.get_by_id_and_version(
                    event.rule_id, event.version
                )
                if event.action == "disable":
                    self.cache.pop(event.rule_id, None)
                else:
                    self.cache[event.rule_id] = rule

                # Commit offset AFTER successful cache update
                self.consumer.commit(msg)

                log.info(
                    "rule_cache_updated",
                    rule_id=event.rule_id,
                    version=event.version,
                    action=event.action,
                )
            except Exception as exc:
                # Do NOT commit — message will be re-consumed on next poll
                log.error(
                    "rule_cache_refresh_failed",
                    rule_id=event.rule_id,
                    error=str(exc),
                )

    @property
    def is_ready(self) -> bool:
        return self._ready.is_set()
```

```python
# app/api/health.py — readiness probe checks rule cache

@router.get("/health/ready")
async def readiness(
    rule_cache: RuleCacheRefresher = Depends(get_rule_cache),
) -> dict:
    if not rule_cache.is_ready:
        raise HTTPException(
            status_code=503,
            detail="Rule cache not yet synchronised"
        )
    return {"status": "ready"}
```

## Consequences

**Positive:**
- < 500ms rule propagation to all pods (vs. up to 60s with TTL polling)
- At-least-once delivery — no missed rule changes on pod restart
- Total ordering — all pods apply the same rule version in the same sequence
- Synchronous refresh — no divergence window between offset commit and cache update
- Versioned rollback — bad rules reversed in < 500ms with full audit trail
- Readiness probe prevents traffic to pods with stale rule cache

**Negative:**
- Kafka consumer dependency added to scoring API pod startup path
- Additional consumer group to monitor: `ras-rule-cache` (@darius)
- Pod startup time increases by ~1–3s (Kafka backlog consumption + DB load)
- Rule cache divergence is possible if PostgreSQL is unavailable at refresh time — mitigated by retry without offset commit

**Operational requirements (@darius):**
- `ras-rule-cache` consumer group lag alert: > 10 messages → P1 (rules may be stale)
- Runbook: `docs/runbooks/rule_cache_stale.md` required before GA
- Consumer group reset procedure documented for disaster recovery

**Audit requirements (@james):**
- Every `rules.changed` Kafka message is consumed by the `ras-audit-elastic` sink
- Full rule change history (create, update, disable, rollback) indexed in Elasticsearch
- Satisfies PCI DSS Requirement 10.2.1(g): logging of all actions by administrators

---

*ADR Directory Version: 1.0.0*
*Owner: Marcus Chen — Chief Risk Architect*
*Format: MADR (Markdown Architectural Decision Records)*
*Review: New ADRs require Architecture Review Board approval*
*Classification: Internal — Engineering Confidential*