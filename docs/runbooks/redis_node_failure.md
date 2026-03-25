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
