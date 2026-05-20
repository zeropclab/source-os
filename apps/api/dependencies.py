"""FastAPI dependency injection."""

import os
from sqlalchemy.ext.asyncio import AsyncSession
from packages.storage.database import async_session


async def get_db():
    """Yield an async database session, closing it after use."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
