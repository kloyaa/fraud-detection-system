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
