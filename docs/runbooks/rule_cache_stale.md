# Rule Cache — Stale or Out of Sync

**Alert:** `kafka_consumer_lag{group="ras-rule-cache"} > 10`  
**Severity:** P1 · **Owner:** `@darius` · **Escalate to:** `@sofia`, `@marcus`

## Why This Is P1

A stale rule cache means scoring pods are applying outdated rules. A new `BLOCK` rule for a confirmed fraud device will not fire until the cache is refreshed. Every transaction scored with a stale cache is a potential missed fraud detection.

## Symptoms
- `kafka_consumer_lag{group="ras-rule-cache"}` > 10
- Rule change published by analyst but not reflected in scoring decisions
- `rule_cache_version` metric diverging across pods

## Diagnosis

```bash
# 1. Consumer lag per partition
kafka-consumer-groups.sh \
  --bootstrap-server $KAFKA_BROKERS \
  --describe --group ras-rule-cache

# 2. Rule cache version per pod
kubectl logs -n risk -l app=ras-scoring-api --tail=200 | \
  jq 'select(.msg=="rule_cache_updated") |
      {pod: .pod_name, rule_id, version, action}'

# 3. PostgreSQL rule versions (source of truth)
psql $DATABASE_URL -c "
  SELECT rule_id, MAX(version) as current_version, is_active
  FROM rules GROUP BY rule_id, is_active
  ORDER BY rule_id;"

# 4. Scoring pod readiness (rule cache must be ready before traffic)
kubectl get pods -n risk -l app=ras-scoring-api \
  -o custom-columns="NAME:.metadata.name,READY:.status.conditions[?(@.type=='Ready')].status"
```

## Fix

```bash
# Option 1: Force rule cache refresh on all pods (rolling restart)
# Pods re-read all rules from PostgreSQL on startup
kubectl rollout restart deployment/ras-scoring-api -n risk

# Monitor readiness — pods won't receive traffic until rule cache is synced
kubectl rollout status deployment/ras-scoring-api -n risk

# Option 2: If only specific pods are stale
kubectl delete pod <stale-pod-name> -n risk
# Kubernetes will reschedule and restart with fresh rule cache

# Verify all pods are on correct rule version after restart
kubectl logs -n risk -l app=ras-scoring-api --tail=50 | \
  jq 'select(.msg=="rule_cache_ready") | {pod: .pod_name, rule_count}'
```

## Prevention
Per ADR-008: Kafka `rules.changed` single partition guarantees total ordering. Offset is committed only after PostgreSQL re-read succeeds. If this alert fires repeatedly, investigate Kafka `rules.changed` topic health.

## Recovery Criteria
`kafka_consumer_lag{group="ras-rule-cache"} = 0` + all pods showing same rule version → resolve alert.
