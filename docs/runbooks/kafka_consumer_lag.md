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
