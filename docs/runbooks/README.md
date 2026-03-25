# Risk Assessment System (RAS) — Runbook Library

**Owner:** Darius Okafor (`@darius`) — Staff SRE / Platform Engineer  
**Security Lead:** Priya Nair (`@priya`) — Principal Security Engineer  
**Status:** ⏳ Template (pre-development — verify all commands before production use)  
**On-Call:** https://pagerduty.ras.internal/schedules/ras-oncall  
**Grafana:** https://grafana.ras.internal  

---

## Quick Index

| Runbook | Severity | Owner | Primary Alert |
|---------|----------|-------|---|
| [Scoring API — High Latency](scoring_api_latency.md) | P1 | `@darius` | `ras_scoring_p95_latency_ms > 120` |
| [Scoring API — High Error Rate](scoring_api_errors.md) | P1 | `@darius` | `ras_error_rate > 0.5%` |
| [ML Service — Degraded or Down](ml_service_degraded.md) | P1 | `@darius` | `bentoml_health_check_failing > 30s` |
| [Redis Cluster — Node Failure](redis_node_failure.md) | P1 | `@darius` | `redis_cluster_state != ok` |
| [Rule Cache — Stale or Out of Sync](rule_cache_stale.md) | P1 | `@darius` | `kafka_consumer_lag{group="ras-rule-cache"} > 10` |
| [Cassandra — Node Failure](cassandra_node_failure.md) | P1 | `@darius` | `cassandra_cluster_nodes_down > 0` |
| [Kafka — Consumer Lag Spike](kafka_consumer_lag.md) | P2 | `@darius` | `kafka_consumer_lag{...} > 2000` |
| [PostgreSQL — Replication Lag](postgres_replication_lag.md) | P2 | `@darius` | `pg_replication_lag_seconds > 5` |
| [Regional Failover — us-east-1 Loss](regional_failover.md) | P1 | `@darius` | `cloudflare_health_check_failing{region="us-east-1"}` |
| [Istio — Certificate Rotation](istio_cert_rotation.md) | P2 | `@darius` | `istio_cert_expiry_days < 7` |
| [Security Incident Response](security_incident.md) | P1 | `@priya` | All security alerts |
| [On-Call Escalation Policy](escalation_policy.md) | — | `@darius` | Reference document |
| [Holiday Capacity Planning](holiday_capacity.md) | — | `@darius` | Pre-holiday planning |

---

## By Severity

### P1 (Critical — < 1 hour resolution)

- [Scoring API — High Latency](scoring_api_latency.md) — P95 latency > 120ms; merchant timeouts
- [Scoring API — High Error Rate](scoring_api_errors.md) — Error rate spike > 0.5%
- [ML Service — Degraded or Down](ml_service_degraded.md) — BentoML health check failing; rule-only fallback active
- [Redis Cluster — Node Failure](redis_node_failure.md) — Velocity checks failing; cache unavailable
- [Rule Cache — Stale or Out of Sync](rule_cache_stale.md) — Stale rules → missed fraud detection
- [Cassandra — Node Failure](cassandra_node_failure.md) — Audit log writes failing; degraded mode
- [Regional Failover — us-east-1 Loss](regional_failover.md) — Active-active failover to surviving regions
- [Security Incident Response](security_incident.md) — PAN in logs, credential compromise, active breach

### P2 (High — < 4 hours resolution)

- [Kafka — Consumer Lag Spike](kafka_consumer_lag.md) — Flink feature cache stale; case creation delayed
- [PostgreSQL — Replication Lag](postgres_replication_lag.md) — Analysts see stale data; replication lag > 5s
- [Istio — Certificate Rotation](istio_cert_rotation.md) — Cert expiry warning; routine or emergency rotation

### Reference

- [On-Call Escalation Policy](escalation_policy.md) — Alert routing, response SLAs, escalation paths
- [Holiday Capacity Planning](holiday_capacity.md) — Black Friday prep, scaling strategy, monitoring checklist

---

## By Service

### Scoring API Pipeline
- [Scoring API — High Latency](scoring_api_latency.md) — Identify breaching stage; fix by root cause
- [Scoring API — High Error Rate](scoring_api_errors.md) — Error breakdown; fix by error code
- [Rule Cache — Stale or Out of Sync](rule_cache_stale.md) — Force refresh; verify version consistency

### ML / BentoML
- [ML Service — Degraded or Down](ml_service_degraded.md) — Pod crash, OOM, GPU node unavailable; fallback verification

### Caching & Features
- [Redis Cluster — Node Failure](redis_node_failure.md) — Velocity counter availability; cluster rebalance
- [Kafka — Consumer Lag Spike](kafka_consumer_lag.md) — Consumer pod health; broker overload; partition rebalance

### Data Stores
- [PostgreSQL — Replication Lag](postgres_replication_lag.md) — Long queries blocking replication; WAL accumulation
- [Cassandra — Node Failure](cassandra_node_failure.md) — Single node; quorum loss; DLQ replay

### Infrastructure & Observability
- [Istio — Certificate Rotation](istio_cert_rotation.md) — Workload certs; root CA rotation; emergency rotation
- [Regional Failover — us-east-1 Loss](regional_failover.md) — Cloudflare auto-failover; manual scaling; recovery

### Security & Compliance
- [Security Incident Response](security_incident.md) — PAN, credential compromise, intrusion, model attack

### Operations
- [On-Call Escalation Policy](escalation_policy.md) — Alert routing, SLAs, communication protocol
- [Holiday Capacity Planning](holiday_capacity.md) — Black Friday prep, pre-holiday checklist, peak monitoring

---

## Common Runbook Patterns

### Verify Degraded Mode Is Active
Many runbooks emphasize **graceful degradation**. Before escalating, confirm:
- Scoring continues with partial flags (e.g., `VELOCITY_UNAVAILABLE`, `audit_flag: PENDING`)
- Appropriate fallback is active (e.g., rule-only scoring)
- Decisions are buffered for replay (e.g., Kafka DLQ)

Examples:
- [ML Service — Degraded or Down](ml_service_degraded.md#verify-fallback-is-active) — rule-only fallback with `model_version: rule_only`
- [Cassandra — Node Failure](cassandra_node_failure.md#verify-degraded-mode) — audit log buffered to DLQ with `audit_flag: PENDING`
- [Redis Cluster — Node Failure](redis_node_failure.md#verify-degraded-mode-is-active) — velocity checks fail open with `VELOCITY_UNAVAILABLE`

If degraded mode is NOT active when dependency is down → immediate escalation to `@sofia` (circuit breaker failure).

### Quorum & Consistency
- **Redis:** Cluster must have 3/3 masters; automatic failover for replicas
- **Cassandra:** LOCAL_QUORUM writes need 2/3 nodes per DC. If 2+ nodes down in same DC → quorum lost
- **PostgreSQL:** Replication lag indicates primary performance issues; long queries block replicas

### Kafka Consumer Lag as Signal
If a Kafka consumer group is lagging, check:
1. Consumer pod health (crash-loop, OOM)
2. Producer throughput (traffic spike?)
3. Broker disk (> 80% → reduce retention)
4. Partition imbalance

### Escalation Cascade
- **First 15 min:** Try fix by stage/error code
- **If unresolved → 15 min:** Escalate to secondary owner
- **If unresolved → 30 min:** Page L3 (engineering lead)
- **If unresolved → 1 hour:** Page CISO / VP Eng
- **Security incidents:** Escalate immediately to `@priya` + `@james`

---

## Testing Before Production Use

⚠️ **All runbooks are templates.** Before using in production:
1. Validate all command syntax against your deployed environment
2. Confirm all URLs (Grafana, PagerDuty, internal tools) are correct
3. Test alert thresholds in staging
4. Verify Kubernetes contexts, namespaces, and labels match your setup
5. Confirm on-call contacts and escalation paths in PagerDuty
6. Test DLQ replay and backfill procedures

---

## Maintenance

**Review Cycle:** Quarterly  
**Update Triggers:** After every P1 incident, before major deployment  
**Owner:** Darius Okafor (`@darius`)  

File a GitHub issue if:
- A command fails in your environment
- Alert threshold doesn't match your baseline
- New failure mode discovered
- Recovery procedure changed

---

**Classification:** Internal — Engineering Confidential  
**Version:** 1.0.0  
*Last Updated:* 2026-03-25  
*Next Review:* 2026-06-25
