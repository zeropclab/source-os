"""FastAPI dependency injection."""

from packages.adapters.fixture_source_probe import (
    DispatchingSourceProbeAdapter,
    FixtureProbeTransport,
)
from packages.adapters.github_mission import GitHubFixtureTransport, GitHubPublicTransport
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


def get_github_mission_transport():
    """Return the deterministic transport used for fixture execution and replay."""
    return GitHubFixtureTransport(scenario="issue_with_context")


def get_github_live_transport():
    """Return the public GitHub REST transport used for live mission execution."""
    return GitHubPublicTransport()
