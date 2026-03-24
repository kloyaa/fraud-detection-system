"""Health check routes for production readiness.

GET /v1/health returns simple JSON health status.
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    version: str


@router.get("/health", response_model=HealthResponse, status_code=200)
async def health_check() -> HealthResponse:
    """Simple health endpoint for load balancers and monitoring.

    Returns:
        HealthResponse with status='healthy' and current timestamp
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version="1.0.0",
    )
