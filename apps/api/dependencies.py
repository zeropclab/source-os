"""FastAPI dependency injection."""

from packages.adapters.source_probe import UnsupportedSourceProbeAdapter
from packages.storage.database import async_session


async def get_db():
    """Yield an async database session, closing it after use."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


def get_source_probe_adapter():
    """Return the safe default probe adapter until platform adapters are registered."""
    return UnsupportedSourceProbeAdapter()
