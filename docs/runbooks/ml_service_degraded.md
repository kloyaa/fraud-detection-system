# ML Service — Degraded or Down

**Alert:** `bentoml_health_check_failing > 30s`  
**Severity:** P1 · **Owner:** `@darius` · **Escalate to:** `@yuki`

## Symptoms
- BentoML health check failing
- Scoring API logs: `BENTOML_UNAVAILABLE`
- `ml_fallback_rate` metric > 0
- All decisions showing `model_version: rule_only`

## Verify Fallback Is Active

```bash
# Confirm rule-only fallback is serving — system should degrade gracefully
kubectl logs -n risk -l app=ras-scoring-api --tail=100 | \
  jq 'select(.msg=="risk_decision_made") | .model_version'
# Expected: "rule_only" — this is correct degraded behaviour
```

> If `model_version` is NOT `rule_only` and BentoML is down, the circuit breaker is not working. Escalate to `@sofia` immediately.

## Diagnosis

```bash
# 1. Pod status
kubectl get pods -n risk -l app=ras-bentoml
kubectl describe pod <pod-name> -n risk

# 2. OOM kill check
kubectl describe pod <pod-name> -n risk | grep -i "OOMKilled\|Exit Code"

# 3. GPU node health
kubectl get nodes -l node.kubernetes.io/instance-type=g5.2xlarge
kubectl describe node <gpu-node> | grep -A 5 "Allocatable"

# 4. Model loading errors
kubectl logs -n risk -l app=ras-bentoml --tail=200 | grep -i "error\|failed\|timeout"
```

## Fix

| Cause | Fix |
|---|---|
| Pod crash / OOM | `kubectl rollout restart deployment/ras-bentoml -n risk`. Monitor warmup (ISS-001 pattern: 1000 inferences before ready). |
| GPU node unavailable | Check Karpenter: `kubectl get nodeclaim -n karpenter`. If no GPU nodes available → scale on-demand: `kubectl taint nodes --all nvidia.com/gpu-` |
| Model load failure | Check MLflow registry: `mlflow models list`. Redeploy last known good version. Page `@yuki`. |
| All pods healthy but health check failing | Check BentoML readiness probe path. `curl https://bentoml.ras.internal/healthz` |

## Recovery Criteria
BentoML health check passing + `ml_fallback_rate = 0` for 3 minutes → resolve alert.
