"""Database engine and session management using SQLAlchemy 2.0 async.

Uses asyncpg driver for true async I/O. Never use psycopg2 (blocking).
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

logger = get_logger(__name__)

# SQLAlchemy async engine - pool_size=20 per pod, statement_timeout enforced
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "server_settings": {"application_name": "ras_backend", "jit": "off"},
        "timeout": 10,
        "command_timeout": 2,
    },
)

# Session factory for dependency injection
SessionLocal = async_sessionmaker(
    engine,
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
