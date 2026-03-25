"""Database engine and session management using SQLAlchemy 2.0 async.

Uses asyncpg driver for true async I/O. Never use psycopg2 (blocking).

Per ISS-003: Connection strings include credentials that rotate via Vault.
Engine uses `creator` parameter to build connection strings dynamically with
fresh credentials on each connection, so Vault rotation doesn't require
app restart.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.core.logging import get_logger
from app.core.vault import get_db_credentials

logger = get_logger(__name__)


def _get_database_url() -> str:
    """Construct database URL with fresh credentials from Vault.

    Called on each new connection, ensuring Vault credential rotation
    doesn't require app restart (ISS-003).
    """
    creds = get_db_credentials()
    return (
        f"postgresql+asyncpg://{creds['username']}:{creds['password']}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def _get_database_read_url() -> str:
    """Construct read replica URL with fresh credentials from Vault.

    Falls back to primary if POSTGRES_READ_HOST is not set.
    """
    creds = get_db_credentials()
    host = settings.postgres_read_host or settings.postgres_host
    port = settings.postgres_read_port if settings.postgres_read_host else settings.postgres_port
    return (
        f"postgresql+asyncpg://{creds['username']}:{creds['password']}"
        f"@{host}:{port}/{settings.postgres_db}"
    )


# Primary write engine — pool_size=20 per pod, statement_timeout enforced
# Uses dynamic URL function so credential rotation works without restart
engine = create_async_engine(
    _get_database_url(),
    echo=settings.debug,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour to pick up rotated credentials
    connect_args={
        "server_settings": {"application_name": "ras_backend", "jit": "off"},
        "timeout": 10,
        "command_timeout": 2,
    },
)

# Read replica engine — for analytics queries, smaller pool
# Falls back to primary if POSTGRES_READ_HOST is not set
read_engine = create_async_engine(
    _get_database_read_url(),
    echo=False,
    pool_size=5,
    max_overflow=2,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "server_settings": {"application_name": "ras_backend_read", "jit": "off"},
        "timeout": 10,
        "command_timeout": 5,
    },
)

# Session factory for dependency injection
SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

ReadSessionLocal = async_sessionmaker(
    read_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection for database session.

    Usage in FastAPI:
        @app.get("/endpoint")
        async def handler(session: AsyncSession = Depends(get_db_session)):
            ...

    Yields:
        AsyncSession: Active database session, auto-closed after request.
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_read_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection for read-replica database session.

    Routes analytics and reporting queries to the read replica.
    Falls back to primary when POSTGRES_READ_HOST is not configured.

    Usage in FastAPI:
        @app.get("/analytics")
        async def handler(session: AsyncSession = Depends(get_read_db_session)):
            ...
    """
    async with ReadSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for manual database session management.

    Usage:
        async with get_db() as session:
            result = await session.execute(stmt)
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
