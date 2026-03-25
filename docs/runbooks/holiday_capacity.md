# Holiday Capacity — Peak Traffic Preparation

**Trigger:** 6 weeks before Black Friday (target: 2024-10-14 for Q4 2024)  
**Owner:** `@darius` · **Joint:** `@marcus`

## Context
Black Friday / Cyber Monday peak is estimated at 4x daily average TPS. At Q2 2025 volume (50k TPS baseline), this equals 200k TPS — 2x the current stress ceiling of 100k TPS. Pre-emptive scaling is required.

See capacity plan: `docs/architecture/capacity_plan.md` §9.3

## Pre-Holiday Checklist (6 Weeks Before)

```
[ ] Run load test at 2x expected holiday peak
[ ] Review capacity plan with @marcus — update projections
[ ] Confirm Black Friday scaling strategy with @james
    (merchant rate limiting vs. infrastructure expansion)
[ ] Pre-provision additional GPU nodes for BentoML
[ ] Increase Kafka partition count if throughput headroom < 40%
[ ] Pre-scale Cassandra if disk utilisation > 50%
[ ] Review and update all alert thresholds for holiday baseline
[ ] Brief on-call engineers on holiday runbook
[ ] Confirm PagerDuty escalation policy for holiday period
[ ] Notify @james of expected volume for merchant SLA review
```

## Day-Before Scaling

```bash
# Scale scoring API to holiday minimum
kubectl scale deployment ras-scoring-api -n risk --replicas=30

# Scale BentoML to holiday minimum
kubectl scale deployment ras-bentoml -n risk --replicas=8

# Pre-warm Flink to handle velocity spike
kubectl scale deployment ras-flink-pipeline -n risk --replicas=6

# Verify HPA limits are set for holiday ceiling
kubectl get hpa -n risk ras-scoring-api-hpa -o yaml | \
  grep maxReplicas
# Ensure maxReplicas >= holiday target

# Pre-provision Karpenter node capacity
kubectl apply -f k8s/karpenter/holiday-nodepool.yaml
```

## During Holiday Peak Monitoring

```bash
# Watch real-time TPS vs. capacity
watch -n 5 "kubectl top pods -n risk -l app=ras-scoring-api \
  --sort-by=cpu | head -20"

# Monitor error budget burn rate
# Grafana: https://grafana.ras.internal/d/slo/error-budget
# If burning > 2x normal rate → scale immediately

# Watch Cassandra disk — holiday write volume is highest of year
watch -n 60 "kubectl exec -n cassandra -it cassandra-0 -- \
  nodetool status | grep -E 'UN|DN'"
```

## Post-Holiday Scale-Down

```bash
# Scale down gradually — do not drop replicas abruptly
# Wait 48 hours post-peak before scaling down
# Scale down at 10% per hour to avoid cold-start gaps

kubectl scale deployment ras-scoring-api -n risk --replicas=15
# Wait 30 min, verify P95 stable
kubectl scale deployment ras-scoring-api -n risk --replicas=10
# Return to normal HPA control after 24 hours
```
