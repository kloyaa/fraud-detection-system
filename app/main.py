"""FastAPI application entry point.

Initializes the RAS backend with all dependencies:
- Structured logging
- Database connections
- Middleware (idempotency, CORS, etc)
- Route mounting
- Lifespan management
"""

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.cassandra.client import close_cassandra, init_cassandra
from app.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.redis import close_redis, init_redis
from app.db.engine import engine
from app.health.routes import probes_router, router as health_router
from app.kafka.producer import close_kafka_producer, init_kafka_producer
from app.middleware.idempotency import IdempotencyMiddleware
from app.scoring.routes import router as scoring_router

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracing."""

    async def dispatch(self, request: Request, call_next):
        """Add X-Request-ID header to response."""
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown.

    Startup:
        - Initialize database tables (idempotent via Alembic)
        - Verify database connectivity
        - Verify Redis connectivity

    Shutdown:
        - Close database connections gracefully
        - Close Redis connections gracefully
    """
    # Startup
    setup_logging()
    logger.info("app_startup", environment=settings.environment, version="1.0.0")

    # Log service endpoints
    logger.info(
        "backend_service_endpoints",
        host=settings.api_host,
        port=settings.api_port,
        local_url="http://localhost:8000",
        swagger_ui="http://localhost:8000/docs",
        redoc="http://localhost:8000/redoc",
        openapi_json="http://localhost:8000/openapi.json",
    )

    # Database connectivity check
    try:
        async with engine.begin() as conn:
            await conn.exec_driver_sql("SELECT 1")
        logger.info("database_connected", db=settings.postgres_db)
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        raise

    # Redis connectivity check
    try:
        await init_redis()
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        raise

    # Kafka producer
    try:
        await init_kafka_producer()
    except Exception as e:
        logger.warning("kafka_producer_init_failed", error=str(e))
        # Non-fatal: scoring still works, Kafka publish will be skipped

    # Cassandra audit log
    try:
        await init_cassandra()
    except Exception as e:
        logger.warning("cassandra_init_failed", error=str(e))
        # Non-fatal: scoring still works, Cassandra writes go to DLQ

    yield

    # Shutdown
    logger.info("app_shutdown")
    await close_kafka_producer()
    await close_cassandra()
    await close_redis()
    await engine.dispose()


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application.

    Returns:
        Configured FastAPI instance ready for deployment
    """
    # OpenAPI documentation URLs
    # Disabled in production (enable_docs=False) for security
    docs_url = "/docs" if settings.enable_docs else None
    redoc_url = "/redoc" if settings.enable_docs else None
    openapi_url = "/openapi.json" if settings.enable_docs else None

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description="Production-grade fraud detection and risk scoring platform",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    # Middleware stack (order matters - bottom executes first)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment == "development" else [],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(health_router)
    app.include_router(probes_router)
    app.include_router(scoring_router)

    # Root endpoint
    @app.get("/", tags=["metadata"])
    async def root():
        return {
            "service": "Risk Assessment System (RAS)",
            "version": settings.api_version,
            "environment": settings.environment,
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
