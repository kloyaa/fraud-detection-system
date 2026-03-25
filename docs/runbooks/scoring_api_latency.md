# Scoring API — High Latency

**Alert:** `ras_scoring_p95_latency_ms > 120` for 3 min  
**Severity:** P1 · **Owner:** `@darius` · **Escalate to:** `@sofia`, `@yuki`

## Symptoms
- P95 latency > 120ms in Grafana `ras-scoring/overview`
- HPA scaling but latency not recovering
- Merchant timeout errors increasing

## Diagnosis

```bash
# 1. Identify breaching pipeline stage
kubectl logs -n risk -l app=ras-scoring-api --tail=200 | \
  jq 'select(.msg=="risk_decision_made") |
      {processing_ms, enrichment_ms, feature_ms, ml_ms, db_ms}'

# 2. BentoML inference latency
curl https://bentoml.ras.internal/metrics | \
  grep bentoml_runner_latency_seconds

# 3. Redis latency
redis-cli -c --no-auth-warning -a $REDIS_PASSWORD \
  INFO latency | grep instantaneous

# 4. PgBouncer pool saturation
psql $DATABASE_URL -c \
  "SELECT pool_mode, used, free, waiting FROM pgbouncer.pools;"

# 5. Pod resource saturation
kubectl top pods -n risk -l app=ras-scoring-api --sort-by=cpu
```

## Fix by Stage

| Breaching Stage | Budget | Fix |
|---|---|---|
| Enrichment | > 10ms | Check IPQualityScore API response time. If timing out → enrichment fails open, scoring continues. Verify `enrichment_partial` flag in logs. |
| Feature fetch | > 5ms | Check Redis cluster: `redis-cli cluster info`. FAIL state → `redis_node_failure.md` |
| ML inference | > 25ms | Check BentoML queue depth. Scale pods: `kubectl scale deployment ras-bentoml -n risk --replicas=N` |
| DB write | > 5ms | Check PgBouncer pool. Increase `pool_size` in `k8s/pgbouncer/config.yaml` and rolling restart |
| All stages normal | — | Page `@marcus` — architectural investigation needed |

## Rollback
```bash
# If latency spike follows a deployment
kubectl rollout history deployment/ras-scoring-api -n risk
kubectl rollout undo deployment/ras-scoring-api -n risk
```

## Recovery Criteria
P95 < 100ms sustained for 5 minutes → resolve alert.
