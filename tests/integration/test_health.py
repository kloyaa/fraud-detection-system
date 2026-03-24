"""Health endpoint integration tests."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_health_check(test_client: TestClient) -> None:
    """Health check returns 200 with correct structure."""
    response = test_client.get("/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data


@pytest.mark.integration
def test_root_endpoint(test_client: TestClient) -> None:
    """Root endpoint returns service metadata."""
    response = test_client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Risk Assessment System (RAS)"
    assert data["version"] == "1.0.0"
