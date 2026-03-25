# RAS Runbook Library
## Complete Operational Runbooks — Risk Assessment System

```yaml
owner:          Darius Okafor (@darius) — Staff SRE / Platform Engineer
security:       Priya Nair (@priya) — security_incident.md
status:         ⏳ Template (pre-development — verify all commands before production use)
on_call:        https://pagerduty.ras.internal/schedules/ras-oncall
grafana:        https://grafana.ras.internal
classification: Internal — Engineering Confidential
```

> ⚠️ All runbooks are **templates**. Commands, thresholds, and URLs must be validated against the actual deployed environment before use in production.

---

---
# FILE: docs/runbooks/scoring_api_latency.md
---

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

---

---
# FILE: docs/runbooks/scoring_api_errors.md
---

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

---

---
# FILE: docs/runbooks/ml_service_degraded.md
---

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

---

---
# FILE: docs/runbooks/redis_node_failure.md
---

# Redis Cluster — Node Failure
**Alert:** `redis_cluster_state != ok` OR `redis_connected_slaves < 1`
**Severity:** P1 · **Owner:** `@darius`

## Symptoms
- Redis cluster state: FAIL
- Velocity checks failing open (`VELOCITY_UNAVAILABLE` flag on decisions)
- Feast feature fetch latency spike

## Verify Degraded Mode Is Active

```bash
# Velocity checks should fail open — scoring continues
kubectl logs -n risk -l app=ras-scoring-api --tail=50 | \
  jq 'select(.enrichment_partial==true or .velocity_unavailable==true)'
```

## Diagnosis

```bash
# 1. Cluster health
redis-cli -c --no-auth-warning -a $REDIS_PASSWORD cluster info | \
  grep -E "cluster_state|cluster_slots_fail|cluster_known_nodes"

# 2. Node states
redis-cli -c --no-auth-warning -a $REDIS_PASSWORD cluster nodes | \
  awk '{print $1, $3, $8}'

# 3. Failed slots
redis-cli -c --no-auth-warning -a $REDIS_PASSWORD cluster info | \
  grep cluster_slots_fail
```

## Fix

```bash
# Identify failed node
redis-cli cluster nodes | grep fail

# If replica failure — automatic failover should have occurred
# Verify: cluster nodes | grep master (should show 3 masters)

# If master failure — trigger manual failover from replica
redis-cli -h <replica-host> cluster failover

# If node is unreachable — remove from cluster and add replacement
redis-cli cluster forget <node-id>

# After new node is up — rebalance slots
redis-cli --cluster rebalance <any-node>:6379

# Verify cluster is healthy
redis-cli cluster info | grep cluster_state
# Expected: cluster_state:ok
```

## Recovery Criteria
`cluster_state: ok` + all slots assigned + `redis_connected_slaves >= 1` per master → resolve alert.

---

---
# FILE: docs/runbooks/kafka_consumer_lag.md
---

# Kafka — Consumer Lag Spike
**Alert:** `kafka_consumer_lag{group="ras-scoring-decisions"} > 2000`
**Severity:** P2 · **Owner:** `@darius` · **Escalate to:** `@marcus`

## Symptoms
- Consumer lag growing in Grafana `kafka-overview` dashboard
- Flink velocity features becoming stale (up to window size behind)
- Case creation delayed

## Diagnosis

```bash
# 1. Consumer group lag per partition
kafka-consumer-groups.sh \
  --bootstrap-server $KAFKA_BROKERS \
  --describe --group ras-scoring-decisions

# 2. Producer throughput (is produce rate spiking?)
kafka-topics.sh \
  --bootstrap-server $KAFKA_BROKERS \
  --describe --topic risk.decisions

# 3. Consumer pod health
kubectl get pods -n risk -l app=ras-flink-pipeline
kubectl logs -n risk -l app=ras-flink-pipeline --tail=100 | \
  grep -i "error\|exception\|lag"

# 4. Broker health
kubectl exec -n kafka -it kafka-0 -- \
  kafka-broker-api-versions.sh --bootstrap-server localhost:9092
```

## Fix

| Cause | Fix |
|---|---|
| Consumer pod crash | `kubectl rollout restart deployment/ras-flink-pipeline -n risk` |
| Produce spike (traffic burst) | Scale consumer pods: `kubectl scale deployment ras-flink-pipeline -n risk --replicas=N` |
| Partition imbalance | Trigger rebalance: `kafka-preferred-replica-election.sh --bootstrap-server $KAFKA_BROKERS` |
| Broker overloaded | Check broker CPU/disk. If disk > 80% → see §Disk pressure below |
| DLQ growing | Check `risk.decisions.dlq` lag. If > 0 → investigate failed messages |

```bash
# DLQ inspection
kafka-console-consumer.sh \
  --bootstrap-server $KAFKA_BROKERS \
  --topic risk.decisions.dlq \
  --from-beginning \
  --max-messages 10
```

## Disk Pressure on Broker

```bash
# Check broker disk
kubectl exec -n kafka -it kafka-0 -- df -h /var/kafka-logs

# If > 80%: reduce retention temporarily
kafka-configs.sh \
  --bootstrap-server $KAFKA_BROKERS \
  --entity-type topics \
  --entity-name risk.decisions \
  --alter \
  --add-config retention.ms=86400000   # Reduce to 1 day temporarily
```

## Recovery Criteria
Consumer lag < 500ms sustained for 5 minutes → resolve alert.

---

---
# FILE: docs/runbooks/postgres_replication_lag.md
---

# PostgreSQL — Replication Lag
**Alert:** `pg_replication_lag_seconds > 5`
**Severity:** P2 · **Owner:** `@darius` · **Escalate to:** `@sofia`

## Symptoms
- Replication lag > 5 seconds in Grafana
- Analyst queries on read replicas returning stale data
- Case management dashboard showing outdated queue

## Diagnosis

```bash
# 1. Replication lag on primary
psql $PRIMARY_DATABASE_URL -c "
  SELECT client_addr,
         state,
         sent_lsn,
         write_lsn,
         flush_lsn,
         replay_lsn,
         (sent_lsn - replay_lsn) AS replication_lag_bytes
  FROM pg_stat_replication;"

# 2. Long-running queries blocking replication
psql $PRIMARY_DATABASE_URL -c "
  SELECT pid, now() - pg_stat_activity.query_start AS duration,
         query, state
  FROM pg_stat_activity
  WHERE state != 'idle'
    AND now() - pg_stat_activity.query_start > interval '30 seconds'
  ORDER BY duration DESC;"

# 3. WAL accumulation
psql $PRIMARY_DATABASE_URL -c "
  SELECT pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0'))
  AS total_wal_size;"
```

## Fix

```bash
# Terminate long-running blocking query
psql $PRIMARY_DATABASE_URL -c \
  "SELECT pg_terminate_backend(<pid>);"

# If replica is significantly behind — check replica logs
kubectl logs -n risk -l app=postgres-replica --tail=200 | \
  grep -i "error\|recovery\|conflict"

# If replica needs resync from scratch
# (last resort — loses replica until resync completes)
# Page @sofia before proceeding
```

## Recovery Criteria
`pg_replication_lag_seconds < 1` sustained for 5 minutes → resolve alert.

---

---
# FILE: docs/runbooks/cassandra_node_failure.md
---

# Cassandra — Node Failure
**Alert:** `cassandra_cluster_nodes_down > 0`
**Severity:** P1 · **Owner:** `@darius`
**ISS-005:** This runbook resolves PRR blocker ISS-005

## Symptoms
- Cassandra node unreachable
- Audit log write failures (`audit_flag: PENDING` on decisions)
- `cassandra_write_latency_p99` spiking

## Verify Degraded Mode

```bash
# Scoring should continue — audit log writes buffer to Kafka DLQ
kubectl logs -n risk -l app=ras-scoring-api --tail=50 | \
  jq 'select(.audit_flag=="PENDING")'
# PENDING is correct degraded behaviour — decisions are buffered
```

> Scoring continues in degraded mode. The Kafka DLQ buffers audit events until Cassandra recovers. No decisions are lost — they are queued for replay.

## Diagnosis

```bash
# 1. Cluster ring status
kubectl exec -n cassandra -it cassandra-0 -- \
  nodetool status

# Expected: UN (Up/Normal) for all nodes
# DN = Down/Normal — node is down but cluster is aware
# Look for: UL (Up/Leaving), DL (Down/Leaving), DJ (Down/Joining)

# 2. Identify which DC has the failure
nodetool status | grep -E "DN|DL|DJ"

# 3. Check if quorum is still achievable
# With RF=3 and LOCAL_QUORUM: need 2/3 nodes per DC
# If 2+ nodes down in same DC — LOCAL_QUORUM writes will fail
nodetool status | grep <datacenter-name> | grep -c "^UN"

# 4. Failed node logs
kubectl logs -n cassandra <failed-pod> --tail=200 | \
  grep -i "error\|fatal\|exception"
```

## Fix

### Scenario A: Single Node Down (Cluster Healthy)

```bash
# Verify remaining nodes can satisfy LOCAL_QUORUM (need 2/3 per DC)
nodetool status | grep <dc-name>
# Must show at least 2 UN nodes per DC

# Attempt pod restart
kubectl delete pod <failed-cassandra-pod> -n cassandra
# Kubernetes will reschedule — monitor rejoin

# Monitor gossip convergence
kubectl exec -n cassandra -it cassandra-0 -- \
  nodetool gossipinfo | grep <failed-node-ip>
# Wait for STATUS:NORMAL
```

### Scenario B: Node Won't Rejoin

```bash
# Remove ghost node from ring
kubectl exec -n cassandra -it cassandra-0 -- \
  nodetool removenode <host-id>

# Provision replacement node
# Karpenter will provision — or manually scale StatefulSet:
kubectl scale statefulset cassandra -n cassandra --replicas=<N+1>

# Bootstrap new node — it will stream data from peers automatically
# Monitor bootstrap progress
kubectl exec -n cassandra -it <new-pod> -- \
  nodetool netstats
```

### Scenario C: 2+ Nodes Down in Same DC (Quorum Lost)

```bash
# LOCAL_QUORUM writes are now failing
# Scoring API falls back to PENDING audit flag
# Escalate to @marcus immediately

# Emergency: temporarily lower consistency (DO NOT do in production
# without @marcus and @priya approval)
# This is a last resort — document in incident report
```

## DLQ Replay After Recovery

```bash
# Once cluster is healthy (all nodes UN), replay buffered audit events
# Verify cluster health first
nodetool status | grep -v "^UN" | grep -v "^$"
# Must return empty output (all nodes UN)

# Trigger DLQ replay
kafka-consumer-groups.sh \
  --bootstrap-server $KAFKA_BROKERS \
  --group ras-dlq-replayer \
  --topic audit.log.dlq \
  --reset-offsets --to-earliest --execute

# Monitor replay progress
kafka-consumer-groups.sh \
  --bootstrap-server $KAFKA_BROKERS \
  --describe --group ras-dlq-replayer
```

## Recovery Criteria
All nodes `UN` in `nodetool status` + DLQ lag = 0 + `cassandra_write_latency_p99 < 5ms` → resolve alert.

---

---
# FILE: docs/runbooks/regional_failover.md
---

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

---

---
# FILE: docs/runbooks/security_incident.md
---

# Security Incident Response
**Severity:** P1 (all security incidents) · **Owner:** `@priya` · **Escalate to:** `@james`, CISO

## Incident Classification

| Type | Examples | Response Time |
|---|---|---|
| **Critical** | PAN in logs, active breach, credential compromise | Immediate (< 15 min) |
| **High** | Suspicious auth pattern, Falco runtime alert, CRITICAL CVE in production | < 1 hour |
| **Medium** | Anomalous feature distribution, failed pentest finding, DLQ security events | < 4 hours |

## Immediate Actions (All Incidents)

```
1. Do NOT attempt to fix before containing
2. Page @priya + @james immediately
3. Open incident channel: #incident-security-YYYYMMDD in Slack
4. Preserve evidence — do NOT restart pods until forensics complete
5. Activate incident log — record every action with timestamp
```

## Scenario A: PAN Detected in Logs

```bash
# STOP all log shipping immediately
kubectl scale deployment loki-promtail -n monitoring --replicas=0

# Identify affected log stream
kubectl logs -n risk -l app=ras-scoring-api --tail=1000 | \
  grep -E '[0-9]{13,16}'

# Contain: isolate affected pod
kubectl label pod <pod-name> -n risk quarantine=true
kubectl apply -f k8s/network-policies/quarantine-policy.yaml

# Page @james — GDPR Art. 33 breach notification assessment
# 72-hour ICO notification window starts NOW
# Document: timestamp of discovery, estimated records affected
```

## Scenario B: Credential / Key Compromise

```bash
# Immediately revoke compromised credential in Vault
vault lease revoke -prefix <lease-prefix>

# If JWT signing key: rotate in Keycloak
# All existing tokens become invalid immediately (~15 min disruption)
# Page @priya for key rotation procedure

# If AWS KMS key: disable key version in AWS console
# Existing encrypted data requires re-encryption with new key
# Page @marcus for re-encryption scope assessment

# Audit: what was accessed with compromised credential?
vault audit list
# Review CloudTrail for KMS key usage
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<key-id>
```

## Scenario C: Active Intrusion (Falco Alert)

```bash
# Isolate affected pod immediately
kubectl label pod <pod-name> -n risk quarantine=true
kubectl apply -f k8s/network-policies/quarantine-policy.yaml

# Capture forensic snapshot BEFORE pod restart
kubectl exec -n risk <pod-name> -- ps aux > /tmp/incident-ps.txt
kubectl exec -n risk <pod-name> -- netstat -tulpn > /tmp/incident-netstat.txt
kubectl logs -n risk <pod-name> --previous > /tmp/incident-logs.txt

# Do NOT restart pod until @priya has reviewed forensics

# Check for lateral movement
kubectl get pods -n risk -o wide | grep -v Running
kubectl logs -n risk --all-containers=true --since=1h | \
  grep -i "connection refused\|permission denied\|unauthorized"
```

## Scenario D: Anomalous Scoring Pattern (Model Attack)

```bash
# Check score distribution anomaly
kubectl logs -n risk -l app=ras-scoring-api --tail=1000 | \
  jq '.score' | sort -n | uniq -c

# Check for systematic low scoring (adversarial evasion attempt)
# If mean score shifted > 40 points vs. baseline → page @yuki

# Temporarily lower decline threshold as defensive measure
# (requires @marcus + @james approval — affects merchant SLA)
```

## Regulatory Notifications

| Obligation | Trigger | Deadline | Owner |
|---|---|---|---|
| ICO (UK GDPR Art. 33) | Personal data breach | 72 hours from discovery | `@james` |
| EDPB (EU GDPR Art. 33) | EU resident data affected | 72 hours | `@james` |
| FinCEN (BSA) | Breach affecting AML records | As soon as practicable | `@james` |
| PCI DSS | CHD breach | Immediately + forensics | `@james` + QSA |
| Merchant notification | Any breach affecting merchant data | Per merchant contract SLA | `@james` |

## Post-Incident

```
Within 24h: Incident timeline documented
Within 48h: Root cause identified
Within 72h: Regulatory notifications filed (if required)
Within 7d:  Post-mortem published to #engineering
Within 30d: Preventive controls implemented + verified
```

---

---
# FILE: docs/runbooks/istio_cert_rotation.md
---

# Istio — Certificate Rotation
**Alert:** `istio_cert_expiry_days < 7`
**Severity:** P2 · **Owner:** `@darius`

## Overview

Istio Citadel CA rotates workload certificates every 24 hours automatically. This runbook covers manual rotation for the Citadel root CA (annual) and emergency rotation on compromise.

## Verify Current Certificate Status

```bash
# Check workload cert expiry across all pods
istioctl proxy-config secret <pod-name>.<namespace> | \
  grep -E "NAME|VALID"

# Check Citadel CA cert expiry
kubectl get secret -n istio-system istio-ca-secret -o jsonpath=\
  '{.data.ca-cert\.pem}' | base64 -d | \
  openssl x509 -noout -dates
```

## Routine Workload Cert Rotation (Automatic)

Workload certs rotate every 24 hours without intervention. If a pod is showing an expired cert:

```bash
# Force cert refresh by restarting the pod
kubectl rollout restart deployment/<deployment-name> -n risk

# Verify new cert
istioctl proxy-config secret <new-pod>.<namespace> | grep VALID
```

## Root CA Rotation (Annual — Planned)

```bash
# Step 1: Generate new root CA
# (Follow Istio documentation for CA rotation with zero downtime)
# https://istio.io/latest/docs/tasks/security/cert-management/plugin-ca-cert/

# Step 2: Add new CA to trust bundle (dual-CA period)
kubectl create secret generic cacerts -n istio-system \
  --from-file=ca-cert.pem=new-ca-cert.pem \
  --from-file=ca-key.pem=new-ca-key.pem \
  --from-file=root-cert.pem=new-root-cert.pem \
  --from-file=cert-chain.pem=new-cert-chain.pem \
  --dry-run=client -o yaml | kubectl apply -f -

# Step 3: Rolling restart of istiod
kubectl rollout restart deployment/istiod -n istio-system

# Step 4: Rolling restart of all workloads to pick up new certs
for ns in risk kafka; do
  kubectl rollout restart deployment -n $ns
done

# Step 5: Verify all workloads have new cert
istioctl analyze -n risk
```

## Emergency Rotation (Cert Compromise)

```bash
# Immediately revoke all current certs by rotating root CA
# This will cause brief disruption to all internal services (~2 min)
# Page @priya + @marcus before proceeding

# Follow Root CA Rotation procedure above with urgency
# All pods will fail mTLS until they receive new certs
# Karpenter will handle pod restarts
```

## Recovery Criteria
All pods showing valid certs with new CA → resolve alert.

---

---
# FILE: docs/runbooks/escalation_policy.md
---

# On-Call Escalation Policy
**Owner:** `@darius` · **PagerDuty:** https://pagerduty.ras.internal

## On-Call Rotation

| Tier | Role | Responds To | Escalates To |
|---|---|---|---|
| L1 | SRE On-Call | All P1/P2 alerts | L2 after 15 min no resolution |
| L2 | Senior SRE / Service Owner | L1 escalation | L3 after 30 min |
| L3 | Engineering Lead (`@marcus` / `@sofia`) | L2 escalation | CISO / VP Eng after 1 hour |
| Security | `@priya` | Any security alert | CISO immediately |
| Compliance | `@james` | Breach / SAR / regulatory | Legal + CISO immediately |

## Alert Routing by Service

| Alert | Primary | Secondary | Escalate If |
|---|---|---|---|
| Scoring API latency P1 | `@darius` | `@sofia` | Not resolved in 15 min |
| ML service down | `@darius` | `@yuki` | Fallback not active in 5 min |
| Cassandra node down | `@darius` | `@marcus` | Quorum lost |
| Security incident | `@priya` | `@james` | Immediately |
| SAR deadline at risk | `@james` | CISO | Immediately |
| Regional failover | `@darius` | `@marcus` | 30 min post-failover |
| PRR blocker discovered in prod | `@aisha` | All leads | Immediately |

## Response Time SLAs

| Severity | Acknowledge | First Update | Resolution Target |
|---|---|---|---|
| P1 | 5 min | 15 min | 1 hour |
| P2 | 15 min | 30 min | 4 hours |
| P3 | 30 min | 2 hours | 24 hours |

## Communication Protocol

```
P1 Incident Open:
  1. Acknowledge in PagerDuty
  2. Open #incident-YYYYMMDD-<service> Slack channel
  3. Post status every 15 min until resolved
  4. Notify @james if merchant SLA impact (> 5 min P1)

P1 Incident Resolved:
  1. Resolve in PagerDuty
  2. Post resolution summary in incident channel
  3. Schedule post-mortem within 48 hours
  4. File post-mortem in docs/postmortems/

Merchant Communication:
  Any P1 lasting > 5 minutes → @james notifies affected merchants
  per contractual SLA obligations
```

## Handoff Protocol (Shift Change)

```
Outgoing on-call must:
  1. Document all active incidents in PagerDuty
  2. List any degraded services or known issues
  3. Hand off any open investigation to incoming on-call
  4. Confirm handoff acknowledged in #on-call Slack channel
```

---

---
# FILE: docs/runbooks/rule_cache_stale.md
---

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

---

---
# FILE: docs/runbooks/holiday_capacity.md
---

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

---

*Runbook Library Version: 1.0.0*
*Owner: Darius Okafor — Staff SRE / Platform Engineer*
*Status: ⏳ Template — validate all commands before production use*
*Review Cycle: Quarterly · After every P1 incident*
*Classification: Internal — Engineering Confidential*