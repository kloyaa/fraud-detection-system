# Scoring API — High Error Rate

**Alert:** `ras_error_rate > 0.5%` for 2 min  
**Severity:** P1 · **Owner:** `@darius` · **Escalate to:** `@sofia`

## Symptoms
- HTTP 5xx rate rising in Grafana
- Kafka `risk.decisions` consumer lag growing
- Merchant integration errors

## Diagnosis

```bash
# 1. Error breakdown by type
kubectl logs -n risk -l app=ras-scoring-api --tail=300 | \
  jq 'select(.level=="error") | .error_code' | \
  sort | uniq -c | sort -rn

# 2. Pod crash-loop check
kubectl get pods -n risk -l app=ras-scoring-api
kubectl describe pod <pod-name> -n risk | grep -A 10 "Last State"

# 3. Recent deployments
kubectl rollout history deployment/ras-scoring-api -n risk

# 4. Dependency health
kubectl get pods -n risk | grep -E "bentoml|pgbouncer|redis"
```

## Fix by Error Code

| Error Code | Cause | Fix |
|---|---|---|
| `DB_CONNECTION_FAILED` | PgBouncer pool exhausted | `kubectl rollout restart deployment/pgbouncer -n risk` |
| `REDIS_TIMEOUT` | Redis cluster degraded | See `redis_node_failure.md`. Velocity checks fail open automatically. |
| `BENTOML_UNAVAILABLE` | BentoML pod crash | `kubectl rollout restart deployment/ras-bentoml -n risk`. Rule-only fallback activates. |
| `KAFKA_PUBLISH_FAILED` | Kafka broker issue | See `kafka_consumer_lag.md`. Decision still returned to client — Kafka write is async. |
| `VALIDATION_ERROR` spike | Bad merchant payload | Not a system error. Identify merchant via logs and notify. |
| `500` after deployment | Bad release | `kubectl rollout undo deployment/ras-scoring-api -n risk` |

## Recovery Criteria
Error rate < 0.1% sustained for 5 minutes → resolve alert.
