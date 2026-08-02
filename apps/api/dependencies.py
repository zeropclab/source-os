"""FastAPI dependency injection."""

from packages.adapters.fixture_source_probe import (
    DispatchingSourceProbeAdapter,
    FixtureProbeTransport,
)
from packages.storage.database import async_session


async def get_db():
    """Yield an async database session, closing it after use."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


def get_source_probe_adapter():
    """Return the dispatcher with an explicit deterministic reference adapter."""
    return DispatchingSourceProbeAdapter()


def get_source_probe_transport():
    """Return the no-network transport used by the reference probe adapter."""
    return FixtureProbeTransport()
