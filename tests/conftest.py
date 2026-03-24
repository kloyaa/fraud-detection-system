"""Pytest configuration and shared fixtures.

Fixtures for database setup, FastAPI test client, and cleanup.
Uses Testcontainers for real PostgreSQL/Redis (not mocks).
"""

import asyncio
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app.config import Settings, settings
from app.db.engine import SessionLocal
from app.db.models import Base
from app.main import create_app


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """Provide event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container() -> PostgresContainer:
    """Start a real PostgreSQL container for test suite.

    Warning: This is slow but ensures zero-downtime migration patterns work.
    """
    container = PostgresContainer(
        image="postgres:16-alpine",
        driver="psycopg",
    )
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def redis_container() -> RedisContainer:
    """Start a real Redis container for test suite."""
    container = RedisContainer(image="redis:7-alpine")
    container.start()
    yield container
    container.stop()


@pytest.fixture
def test_settings(
    postgres_container: PostgresContainer, redis_container: RedisContainer
) -> Settings:
    """Override settings to use test containers."""
    test_settings = Settings(
        environment="testing",
        debug=True,
        postgres_user=postgres_container.username,
        postgres_password=postgres_container.password,
        postgres_host=postgres_container.get_container_host_ip(),
        postgres_port=postgres_container.get_exposed_port("5432"),
        postgres_db=postgres_container.dbname,
        redis_host=redis_container.get_container_host_ip(),
        redis_port=redis_container.get_exposed_port(6379),
    )
    return test_settings


@pytest.fixture
async def db_engine(test_settings: Settings):
    """Create test database engine with test tables."""
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide test database session."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def test_app(db_engine) -> AsyncGenerator[FastAPI, None]:
    """Create FastAPI test app with test database engine override."""
    from app.db.engine import get_db_session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    app = create_app()
    
    # Create test-specific session maker
    test_async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    
    # Override the get_db_session dependency to use test database
    async def override_get_db_session():
        async with test_async_session_maker() as session:
            yield session
    
    app.dependency_overrides[get_db_session] = override_get_db_session
    
    yield app
    
    # Cleanup overrides
    app.dependency_overrides.clear()


@pytest.fixture
def test_client(test_app) -> TestClient:
    """HTTP client for sync tests."""
    return TestClient(test_app)


@pytest.fixture
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for async tests."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
