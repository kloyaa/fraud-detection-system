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
