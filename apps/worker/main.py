"""Run the durable Acquisition Mission worker process."""

import argparse
import asyncio
import os
import socket
import uuid

from packages.adapters.github_mission import GitHubFixtureTransport, GitHubPublicTransport
from packages.storage.database import async_session

from .mission_runs import process_one_mission_run


async def _process_once(worker_id: str, lease_seconds: int) -> bool:
    async with async_session() as db:
        result = await process_one_mission_run(
            db,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
            fixture_transport=GitHubFixtureTransport(scenario="issue_with_context"),
            live_transport=GitHubPublicTransport(),
        )
    return result is not None


async def _run(worker_id: str, lease_seconds: int, poll_seconds: float, once: bool) -> None:
    while True:
        processed = await _process_once(worker_id, lease_seconds)
        if once:
            return
        if not processed:
            await asyncio.sleep(poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process scheduled SourceOS acquisition missions")
    parser.add_argument("--once", action="store_true", help="Process at most one run, then exit")
    parser.add_argument("--lease-seconds", type=int, default=120)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()
    if args.lease_seconds <= 0 or args.poll_seconds <= 0:
        parser.error("lease and poll durations must be positive")
    worker_id = os.getenv("SOURCEOS_WORKER_ID", f"{socket.gethostname()}-{uuid.uuid4()}")
    asyncio.run(_run(worker_id, args.lease_seconds, args.poll_seconds, args.once))


if __name__ == "__main__":
    main()
