"""Health endpoint integration tests."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_health_check(test_client: TestClient) -> None:
    """Legacy health check returns 200 with correct structure."""
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


@pytest.mark.integration
def test_liveness_probe(test_client: TestClient) -> None:
    """Liveness probe always returns 200 — process is alive."""
    response = test_client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


@pytest.mark.integration
def test_readiness_probe_healthy(test_client: TestClient) -> None:
    """Readiness probe returns 200 when DB and Redis are reachable."""
    response = test_client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["redis"] == "ok"
    assert "timestamp" in data
