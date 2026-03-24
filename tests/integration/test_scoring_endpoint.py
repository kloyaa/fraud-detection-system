"""Integration tests for POST /v1/risk/score endpoint.

Tests the full scoring flow including:
- Request validation
- Scoring engine execution
- Database persistence
- Idempotency
- Error handling
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RiskAssessment


@pytest.mark.asyncio
async def test_score_endpoint_success(async_client: AsyncClient, db_session: AsyncSession):
    """Successful scoring request should return 200 with complete response."""
    payload = {
        "transaction_id": "txn_itest_001",
        "customer_id": "cust_itest_001",
        "amount_cents": 10000,
        "currency": "USD",
        "merchant_id": "mch_itest_001",
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_test_001"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "request_id" in data
    assert data["transaction_id"] == "txn_itest_001"
    assert "risk_score" in data
    assert "risk_level" in data
    assert "decision" in data
    assert data["decision"] in ["APPROVE", "REVIEW", "DECLINE"]
    assert data["processing_ms"] >= 0
    assert "engine_version" in data


@pytest.mark.asyncio
async def test_score_endpoint_persists_to_database(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Scoring request should persist to risk_assessments table."""
    payload = {
        "transaction_id": "txn_itest_002",
        "customer_id": "cust_itest_002",
        "amount_cents": 50000,
        "currency": "USD",
        "merchant_id": "mch_itest_002",
        "merchant_category": "5411",
        "merchant_country": "US",
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_test_002"},
    )

    assert response.status_code == 200

    # Verify record in database
    stmt = select(RiskAssessment).where(
        RiskAssessment.transaction_id == "txn_itest_002"
    )
    result = await db_session.execute(stmt)
    assessment = result.scalar_one_or_none()

    assert assessment is not None
    assert assessment.customer_id == "cust_itest_002"
    assert assessment.amount == 500.0  # 50000 cents = $500
    assert assessment.currency == "USD"
    assert assessment.merchant_category == "5411"
    assert assessment.merchant_country == "US"
    assert assessment.decision in ["APPROVE", "REVIEW", "DECLINE"]


@pytest.mark.asyncio
async def test_score_endpoint_validation_missing_required_field(
    async_client: AsyncClient,
):
    """Missing required field should return 422."""
    payload = {
        "transaction_id": "txn_itest_003",
        # Missing customer_id
        "amount_cents": 10000,
        "currency": "USD",
        "merchant_id": "mch_itest_003",
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_test_003"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_score_endpoint_validation_invalid_currency(
    async_client: AsyncClient,
):
    """Invalid currency code should return 422."""
    payload = {
        "transaction_id": "txn_itest_004",
        "customer_id": "cust_itest_004",
        "amount_cents": 10000,
        "currency": "USDA",  # Invalid
        "merchant_id": "mch_itest_004",
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_test_004"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_score_endpoint_validation_invalid_amount(
    async_client: AsyncClient,
):
    """Invalid amount (< 0) should return 422."""
    payload = {
        "transaction_id": "txn_itest_005",
        "customer_id": "cust_itest_005",
        "amount_cents": -100,  # Invalid (must be > 0)
        "currency": "USD",
        "merchant_id": "mch_itest_005",
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_test_005"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_score_endpoint_test_mode(
    async_client: AsyncClient, db_session: AsyncSession
):
    """TEST_ prefixed customer should be low risk."""
    payload = {
        "transaction_id": "txn_itest_test",
        "customer_id": "TEST_customer_001",
        "amount_cents": 10_000_000,  # Huge amount
        "currency": "USD",
        "merchant_id": "mch_itest_test",
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_test_mode"},
    )

    assert response.status_code == 200
    data = response.json()

    # Even with huge amount, TEST_ should be low risk
    assert data["risk_level"] == "LOW"


@pytest.mark.asyncio
async def test_score_endpoint_idempotency(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Same Idempotency-Key should return cached result."""
    payload = {
        "transaction_id": "txn_itest_idem_001",
        "customer_id": "cust_itest_idem_001",
        "amount_cents": 10000,
        "currency": "USD",
        "merchant_id": "mch_itest_idem_001",
    }

    idempotency_key = "idem_repeated_key"

    # First request
    response1 = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": idempotency_key},
    )

    assert response1.status_code == 200
    data1 = response1.json()

    # Second request with same key
    response2 = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": idempotency_key},
    )

    assert response2.status_code == 200
    data2 = response2.json()

    # Results should be identical (except processing_ms which may differ for cache hits)
    assert data1["transaction_id"] == data2["transaction_id"]
    assert data1["risk_score"] == data2["risk_score"]
    assert data1["risk_level"] == data2["risk_level"]
    assert data1["decision"] == data2["decision"]
    assert data1["reason_codes"] == data2["reason_codes"]
    # Cache hits should have lower or equal processing_ms
    assert data2["processing_ms"] <= data1["processing_ms"]

    # Should only have one DB record
    stmt = select(RiskAssessment).where(
        RiskAssessment.idempotency_key == idempotency_key
    )
    result = await db_session.execute(stmt)
    assessments = result.scalars().all()

    assert len(assessments) == 1


@pytest.mark.asyncio
async def test_score_endpoint_high_risk_country(
    async_client: AsyncClient, db_session: AsyncSession
):
    """High-risk country should result in higher risk."""
    payload = {
        "transaction_id": "txn_itest_hrc_001",
        "customer_id": "cust_itest_hrc_001",
        "amount_cents": 10000,
        "currency": "USD",
        "merchant_id": "mch_itest_hrc_001",
        "merchant_country": "NG",  # High-risk: Nigeria
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_hrc_001"},
    )

    assert response.status_code == 200
    data = response.json()

    # Should trigger high-risk country rule
    assert data["risk_level"] in ["MEDIUM", "HIGH", "CRITICAL"]
    assert data["decision"] in ["REVIEW", "DECLINE"]
    assert "HIGH_RISK_COUNTRY" in data["reason_codes"]


@pytest.mark.asyncio
async def test_score_endpoint_includes_reason_codes(
    async_client: AsyncClient,
):
    """Response should include reason codes for decision."""
    payload = {
        "transaction_id": "txn_itest_rc_001",
        "customer_id": "cust_itest_rc_001",
        "amount_cents": 600_000,  # Large amount
        "currency": "USD",
        "merchant_id": "mch_itest_rc_001",
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_rc_001"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "reason_codes" in data
    assert isinstance(data["reason_codes"], list)
    # Large amount should trigger reason code
    assert "LARGE_AMOUNT" in data["reason_codes"]


@pytest.mark.asyncio
async def test_score_endpoint_response_includes_metadata(
    async_client: AsyncClient,
):
    """Response should include execution metadata."""
    payload = {
        "transaction_id": "txn_itest_meta_001",
        "customer_id": "cust_itest_meta_001",
        "amount_cents": 5000,
        "currency": "USD",
        "merchant_id": "mch_itest_meta_001",
    }

    response = await async_client.post(
        "/v1/risk/score",
        json=payload,
        headers={"Idempotency-Key": "idem_meta_001"},
    )

    assert response.status_code == 200
    data = response.json()

    # Check metadata fields
    assert data["processing_ms"] > 0
    assert "engine_version" in data
    assert data["engine_version"] == "1.0.0"
