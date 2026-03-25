"""Async Kafka producer for the risk.decisions topic.

Design (per kafka_topics.md):
- Partition key: customer_id (Murmur2 hash % partitions)
  — guarantees all events for a customer land on the same partition
  — enables Flink velocity window computation without cross-partition coordination
- Serialization: JSON for local dev; Avro + Schema Registry in staging/prod
- Reliability: acks=all, enable_idempotence=True
- Non-blocking: callers use asyncio.create_task() — response returned to client first

Local dev note:
  Bootstrap servers = localhost:9094 (external listener from host)
  Inside Docker = kafka:9092 (PLAINTEXT internal listener)
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

TOPIC_RISK_DECISIONS = "risk.decisions"

_producer: Optional[AIOKafkaProducer] = None


async def init_kafka_producer() -> None:
    """Start the global Kafka producer. Called once in app lifespan."""
    global _producer
    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks="all",
        enable_idempotence=True,
        compression_type="lz4",
        linger_ms=5,
        max_batch_size=65536,
        request_timeout_ms=5000,
        retry_backoff_ms=100,
        retries=10,
    )
    await _producer.start()
    logger.info("kafka_producer_started", bootstrap_servers=settings.kafka_bootstrap_servers)


async def close_kafka_producer() -> None:
    """Stop the global Kafka producer. Called in app lifespan shutdown."""
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
        logger.info("kafka_producer_stopped")


def get_kafka_producer() -> Optional[AIOKafkaProducer]:
    return _producer


async def publish_risk_decision(
    request_id: str,
    customer_id: str,
    merchant_id: str,
    amount_cents: int,
    currency: str,
    score_int: int,
    decision: str,
    rules_triggered: list[str],
    processing_ms: int,
    requires_review: bool,
    region: str = "us-east-1",
) -> Optional[int]:
    """Publish a risk decision to the risk.decisions Kafka topic.

    Returns the Kafka partition offset on success, None on failure.
    Logs errors but never raises — scoring is not blocked by Kafka.
    """
    if _producer is None:
        logger.warning("kafka_producer_unavailable", request_id=request_id)
        return None

    message = {
        "request_id": request_id,
        "customer_id": customer_id,
        "merchant_id": merchant_id,
        "amount_cents": amount_cents,
        "currency": currency,
        "score": score_int,
        "decision": decision,
        "rules_triggered": rules_triggered,
        "model_version": "rule-only-v1",
        "processing_ms": processing_ms,
        "requires_review": requires_review,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "region": region,
        "schema_version": "1.0.0",
    }

    try:
        record_metadata = await _producer.send_and_wait(
            TOPIC_RISK_DECISIONS,
            key=customer_id,
            value=message,
        )
        logger.info(
            "risk_decision_published",
            request_id=request_id,
            topic=TOPIC_RISK_DECISIONS,
            partition=record_metadata.partition,
            offset=record_metadata.offset,
        )
        return record_metadata.offset
    except KafkaError as e:
        logger.error(
            "kafka_publish_failed",
            request_id=request_id,
            topic=TOPIC_RISK_DECISIONS,
            error=str(e),
        )
        return None
    except Exception as e:
        logger.error(
            "kafka_publish_unexpected_error",
            request_id=request_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return None
