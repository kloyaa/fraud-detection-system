"""Scoring endpoint integration tests.

Tests the POST /v1/risk/score skeleton endpoint.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_score_endpoint_missing_idempotency_key(test_client: TestClient) -> None:
    """POST /v1/risk/score without Idempotency-Key returns 422."""
    payload = {
        "transaction_id": "txn_12345",
        "customer_id": "cust_67890",
        "amount_cents": 10000,
        "merchant_id": "merch_aaa",
        "currency": "USD",
    }

    response = test_client.post("/v1/risk/score", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "MISSING_IDEMPOTENCY_KEY"


@pytest.mark.integration
def test_score_endpoint_valid_request(test_client: TestClient) -> None:
    """POST /v1/risk/score with valid Idempotency-Key returns 200."""
    payload = {
        "transaction_id": "txn_12345",
        "customer_id": "cust_67890",
        "amount_cents": 10000,
        "merchant_id": "merch_aaa",
        "currency": "USD",
    }
    headers = {"Idempotency-Key": "idempotency_key_test_001"}

    response = test_client.post("/v1/risk/score", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert data["risk_score"] == "0.3500"
    assert data["risk_tier"] == "MEDIUM"
    assert data["decision"] == "REVIEW"


@pytest.mark.integration
def test_score_endpoint_validation_error(test_client: TestClient) -> None:
    """POST /v1/risk/score with invalid payload returns 422."""
    payload = {
        "transaction_id": "",  # Empty - validation error
        "customer_id": "cust_67890",
        "amount_cents": 10000,
        "merchant_id": "merch_aaa",
    }
    headers = {"Idempotency-Key": "idempotency_key_test_002"}

    response = test_client.post("/v1/risk/score", json=payload, headers=headers)

    assert response.status_code == 422
    # Pydantic validation error
