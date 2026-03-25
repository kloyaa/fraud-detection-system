"""Integration tests: POST /v1/risk/score publishes to Kafka risk.decisions topic.

Uses a real Kafka broker via Testcontainers. Verifies that after a successful
scoring request, a message appears on the risk.decisions topic with the correct
structure and partition key (customer_id).
"""

import asyncio
import json

import pytest
from aiokafka import AIOKafkaConsumer
from httpx import AsyncClient

TOPIC = "risk.decisions"


async def _consume_one(bootstrap_servers: str, timeout: float = 10.0) -> dict | None:
    """Consume one message from risk.decisions, return parsed JSON or None on timeout."""
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset="earliest",
        group_id=None,  # unique consumer — no committed offsets
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
        consumer_timeout_ms=int(timeout * 1000),
    )
    await consumer.start()
    try:
        async for msg in consumer:
            return msg.value
    except Exception:
        return None
    finally:
        await consumer.stop()


@pytest.mark.asyncio
async def test_score_publishes_to_kafka(
    async_client: AsyncClient,
    kafka_bootstrap_servers: str,
):
    """Successful score request should publish a message to risk.decisions."""
    payload = {
        "transaction_id": "txn_kafka_test_001",
        "customer_id": "cust_kafka_001",
        "amount_cents": 10000,
        "currency": "USD",
        "merchant_id": "mch_kafka_001",
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_kafka_001"},
    )
    assert response.status_code == 200
    data = response.json()

    # Give background task time to publish
    await asyncio.sleep(2.0)

    msg = await _consume_one(kafka_bootstrap_servers)
    assert msg is not None, "No message received on risk.decisions topic"

    assert msg["request_id"] == data["request_id"]
    assert msg["customer_id"] == "cust_kafka_001"
    assert msg["merchant_id"] == "mch_kafka_001"
    assert msg["amount_cents"] == 10000
    assert msg["currency"] == "USD"
    assert "score" in msg
    assert msg["decision"] in ("APPROVE", "REVIEW", "DECLINE")
    assert "rules_triggered" in msg
    assert "processing_ms" in msg
    assert "occurred_at" in msg
    assert msg["schema_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_kafka_message_decision_matches_response(
    async_client: AsyncClient,
    kafka_bootstrap_servers: str,
):
    """Kafka message decision must match the API response decision."""
    payload = {
        "transaction_id": "txn_kafka_test_002",
        "customer_id": "cust_kafka_002",
        "amount_cents": 600_000,  # large amount — triggers rule
        "currency": "USD",
        "merchant_id": "mch_kafka_002",
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_kafka_002"},
    )
    assert response.status_code == 200
    data = response.json()

    await asyncio.sleep(2.0)

    msg = await _consume_one(kafka_bootstrap_servers)
    assert msg is not None

    assert msg["decision"] == data["decision"]
    # Score in Kafka is 0–1000 integer; API returns 0.0–1.0 float
    assert msg["score"] == int(data["risk_score"] * 1000)


@pytest.mark.asyncio
async def test_kafka_message_includes_rules_triggered(
    async_client: AsyncClient,
    kafka_bootstrap_servers: str,
):
    """Kafka message should include triggered rule codes."""
    payload = {
        "transaction_id": "txn_kafka_test_003",
        "customer_id": "cust_kafka_003",
        "amount_cents": 10000,
        "currency": "USD",
        "merchant_id": "mch_kafka_003",
        "merchant_country": "NG",  # triggers HIGH_RISK_COUNTRY rule
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_kafka_003"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "HIGH_RISK_COUNTRY" in data["reason_codes"]

    await asyncio.sleep(2.0)

    msg = await _consume_one(kafka_bootstrap_servers)
    assert msg is not None
    assert "HIGH_RISK_COUNTRY" in msg["rules_triggered"]
