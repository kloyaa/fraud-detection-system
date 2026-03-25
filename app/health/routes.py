"""Health check routes for production readiness and Kubernetes probes.

Three endpoints:
  GET /v1/health        — Legacy health check (backward compat, used by docker-compose)
  GET /health/live      — Kubernetes liveness probe (is the process alive?)
  GET /health/ready     — Kubernetes readiness probe (can the pod serve traffic?)
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.db.engine import get_db_session

logger = get_logger(__name__)

# Legacy versioned router (backward compat)
router = APIRouter(prefix="/v1", tags=["health"])

# Kubernetes probe router (no version prefix — probes hit these directly)
probes_router = APIRouter(prefix="/health", tags=["probes"])


class HealthResponse(BaseModel):
    """Legacy health check response."""

    status: str
    timestamp: datetime
    version: str


class LivenessResponse(BaseModel):
    """Liveness probe response — process is alive."""

    status: str
    timestamp: datetime


class ReadinessResponse(BaseModel):
    """Readiness probe response — pod can serve traffic."""

    status: str
    checks: dict[str, str]
    timestamp: datetime


@router.get("/health", response_model=HealthResponse, status_code=200)
async def health_check() -> HealthResponse:
    """Legacy health endpoint for docker-compose and load balancers.

    Returns:
        HealthResponse with status='healthy' and current timestamp.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version="1.0.0",
    )


@probes_router.get("/live", response_model=LivenessResponse, status_code=200)
async def liveness() -> LivenessResponse:
    """Kubernetes liveness probe — is the process alive?

    Returns 200 unconditionally as long as the process can handle requests.
    Never checks external dependencies — a DB failure should NOT restart the pod.
    Only restarts are warranted for true deadlocks or fatal process failures.

    Returns:
        LivenessResponse with status='alive'.
    """
    return LivenessResponse(
        status="alive",
        timestamp=datetime.now(timezone.utc),
    )


@probes_router.get(
    "/ready",
    responses={
        200: {"description": "Pod is ready to serve traffic"},
        503: {"description": "Pod is not ready — dependency check failed"},
    },
)
async def readiness(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    """Kubernetes readiness probe — can the pod serve traffic?

    Performs real connectivity checks against PostgreSQL and Redis.
    Returns 503 if either dependency is unreachable, which removes the pod
    from the load balancer rotation until dependencies recover.

    Returns:
        200 with status='ready' if all checks pass.
        503 with status='not_ready' and per-check details if any check fails.
    """
    checks: dict[str, str] = {}
    all_healthy = True

    # Database check — SELECT 1 via the injected session
    try:
        await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = "error"
        all_healthy = False
        logger.warning("readiness_db_check_failed", error=str(exc))

    # Redis check — PING
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = "error"
        all_healthy = False
        logger.warning("readiness_redis_check_failed", error=str(exc))

    payload = ReadinessResponse(
        status="ready" if all_healthy else "not_ready",
        checks=checks,
        timestamp=datetime.now(timezone.utc),
    )

    return JSONResponse(
        content=payload.model_dump(mode="json"),
        status_code=200 if all_healthy else 503,
    )
