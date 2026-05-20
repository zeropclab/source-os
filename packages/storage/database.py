"""Async SQLAlchemy engine and session factory."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Ensure .env is loaded before reading DATABASE_URL
_load_paths = [Path(__file__).resolve().parent.parent.parent / ".env"]
for _p in _load_paths:
    if _p.exists():
        load_dotenv(_p)
        break

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:sourceos@localhost:5432/sourceos")

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5, max_overflow=10)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
