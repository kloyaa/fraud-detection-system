"""Integration tests: POST /v1/risk/score writes audit event to Cassandra.

Uses a real Cassandra node via Testcontainers. Verifies that after a successful
scoring request, a row appears in the risk_events table.
"""

import asyncio

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_score_writes_to_cassandra(
    async_client: AsyncClient,
    cassandra_session,
):
    """Successful score request should write a row to Cassandra risk_events."""
    payload = {
        "transaction_id": "txn_cass_test_001",
        "customer_id": "cust_cass_001",
        "amount_cents": 25000,
        "currency": "USD",
        "merchant_id": "mch_cass_001",
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_cass_001"},
    )
    assert response.status_code == 200
    data = response.json()

    # Wait for background Cassandra write to complete
    await asyncio.sleep(3.0)

    rows = cassandra_session.execute(
        "SELECT request_id, decision, score FROM risk_events WHERE customer_id = %s ALLOW FILTERING",
        ("cust_cass_001",),
    )
    rows = list(rows)
    assert len(rows) >= 1

    row = rows[0]
    assert row.request_id == data["request_id"]
    assert row.decision == data["decision"]
    assert row.score == int(data["risk_score"] * 1000)


@pytest.mark.asyncio
async def test_cassandra_event_includes_all_fields(
    async_client: AsyncClient,
    cassandra_session,
):
    """Cassandra risk_events row should include all required audit fields."""
    payload = {
        "transaction_id": "txn_cass_test_002",
        "customer_id": "cust_cass_002",
        "amount_cents": 50000,
        "currency": "EUR",
        "merchant_id": "mch_cass_002",
        "merchant_country": "NG",
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_cass_002"},
    )
    assert response.status_code == 200

    await asyncio.sleep(3.0)

    rows = cassandra_session.execute(
        "SELECT * FROM risk_events WHERE customer_id = %s ALLOW FILTERING",
        ("cust_cass_002",),
    )
    rows = list(rows)
    assert len(rows) >= 1

    row = rows[0]
    assert row.customer_id == "cust_cass_002"
    assert row.merchant_id == "mch_cass_002"
    assert row.amount_cents == 50000
    assert row.currency == "EUR"
    assert row.decision is not None
    assert row.rules_triggered is not None
    assert row.processing_ms >= 0
    assert row.occurred_at is not None
