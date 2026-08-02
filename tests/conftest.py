"""Pytest fixtures for SourceOS tests."""

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from packages.storage.database import Base, database_connection_params

TEST_DB = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:sourceos@localhost:5432/sourceos_test"
)


async def _ensure_test_db():
    """Create test database if it doesn't exist."""
    import asyncpg

    params = database_connection_params(TEST_DB)
    db_name = params.pop("database")

    sys_conn = await asyncpg.connect(database="template1", **params)
    try:
        exists = await sys_conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            await sys_conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await sys_conn.close()


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Per-function engine with fresh tables."""
    await _ensure_test_db()
    _engine = create_async_engine(TEST_DB, echo=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield _engine

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await _engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db(engine):
    """Per-test database session. Tables are recreated per test so no rollback needed."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db):
    """Async HTTP test client with database override."""
    from apps.api.dependencies import get_db
    from apps.api.main import app

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
