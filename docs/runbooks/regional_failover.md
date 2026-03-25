# Regional Failover — us-east-1 Loss

**Alert:** `cloudflare_health_check_failing{region="us-east-1"} > 30s`  
**Severity:** P1 · **Owner:** `@darius` · **Escalate to:** `@marcus`, `@james`

## Overview

RAS is active-active across 3 regions. Cloudflare automatically re-routes traffic within 10–30 seconds. This runbook covers the manual steps needed after automatic failover completes.

```
Normal:     us-east-1 (55%) + eu-west-1 (30%) + ap-southeast-1 (15%)
After fail: eu-west-1 (67%) + ap-southeast-1 (33%)
```

## Verify Automatic Failover

```bash
# 1. Confirm Cloudflare has re-routed traffic
curl -I https://api.ras.internal/health/live \
  -H "X-Forwarded-For: 8.8.8.8"
# Check response header: CF-RAY should show non-us-east-1 datacenter

# 2. Confirm eu-west-1 is serving traffic
kubectl get pods -n risk --context=eu-west-1
kubectl top pods -n risk --context=eu-west-1
# Pod count should have increased via HPA

# 3. Scoring API health in surviving regions
curl https://api.ras.internal/health/ready
```

## Manual Steps (Post-Automatic Failover)

```bash
# 1. Scale up surviving regions to handle full traffic
kubectl scale deployment ras-scoring-api -n risk \
  --context=eu-west-1 --replicas=50
kubectl scale deployment ras-scoring-api -n risk \
  --context=ap-southeast-1 --replicas=25

# 2. Promote PostgreSQL read replica in eu-west-1
# (Only needed if us-east-1 primary is unreachable)
# Page @sofia before executing
aws rds promote-read-replica \
  --db-instance-identifier ras-postgres-eu-west-1-replica \
  --region eu-west-1

# 3. Verify Cassandra LOCAL_QUORUM is satisfied in eu-west-1
kubectl exec -n cassandra --context=eu-west-1 -it cassandra-0 -- \
  nodetool status
# Must show 3x UN nodes in eu-west-1 DC

# 4. Verify Kafka MirrorMaker2 lag
kafka-consumer-groups.sh \
  --bootstrap-server $KAFKA_BROKERS_EU \
  --describe --group mirrormaker2-ras

# 5. Notify @james — SLA impact assessment + merchant communication
```

## In-Flight Request Handling

- Requests in us-east-1 at time of failure → client timeout → client retries with same idempotency key
- Idempotency key deduplication ensures no double-processing on retry
- Merchants should be notified of the ~15–30 second disruption window

## Recovery (us-east-1 Returns)

```bash
# 1. Do NOT automatically re-route traffic back
# Verify us-east-1 is fully healthy first

# 2. Health check all services in us-east-1
kubectl get pods -n risk --context=us-east-1
nodetool status  # Cassandra ring

# 3. Gradually re-route traffic via Cloudflare (5% → 25% → 55%)
# Manual adjustment in Cloudflare dashboard

# 4. If PostgreSQL was promoted in eu-west-1:
# Re-establish replication before failing back
# Page @sofia for replica rebuild procedure
```

## Compliance Note (@james)
Regional failover does not affect data subject rights — Cassandra multi-DC replication ensures audit data is available in all regions. GDPR data residency: EU customer data processed in eu-west-1 only (MirrorMaker2 replicates decisions, not raw PII).

## Recovery Criteria
All regions healthy + traffic distribution restored + Kafka MirrorMaker2 lag < 3s → resolve alert.
