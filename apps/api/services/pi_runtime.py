"""Bounded subprocess bridge to Pi Agent; it never receives database authority."""

import asyncio
import json
import shlex
from pathlib import Path

from apps.api.config import settings


class PiRuntimeError(RuntimeError):
    """A Pi runtime execution failed after its run record was already created."""


def provider_for(model_version: str) -> tuple[str, str]:
    if model_version == "pi-faux-v1":
        return "faux", "sourceos-proposal-faux-v1"
    if not settings.pi_provider or not settings.pi_model:
        raise PiRuntimeError(
            "Pi provider is not configured; set SOURCEOS_PI_PROVIDER and SOURCEOS_PI_MODEL"
        )
    expected = f"{settings.pi_provider}/{settings.pi_model}"
    if model_version != expected:
        raise PiRuntimeError(f"Model version must match configured Pi model: {expected}")
    return settings.pi_provider, settings.pi_model


async def run_pi_proposal(
    *,
    run_id: str,
    task_instruction: str,
    evidence_bundle_hash: str,
    evidence_bundle: list[dict],
    model_version: str,
    budgets: dict,
) -> dict:
    provider, model = provider_for(model_version)
    envelope = {
        "protocol_version": "1.0",
        "message_id": f"agent-run-{run_id}",
        "agent_run_id": run_id,
        "sequence": 1,
        "type": "start",
        "payload": {
            "evidence_bundle_hash": evidence_bundle_hash,
            "task_instruction": task_instruction,
            "citations": [
                str(entry.get("signal_id") or f"{entry.get('kind', 'evidence')}:{entry.get('id')}")
                for entry in evidence_bundle
            ],
            "evidence_bundle": evidence_bundle,
            "provider": provider,
            "model": model,
            "budget": budgets,
        },
    }
    root = Path(__file__).resolve().parents[3]
    process = await asyncio.create_subprocess_exec(
        *shlex.split(settings.pi_runtime_command),
        cwd=root,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(f"{json.dumps(envelope)}\n".encode()),
            timeout=settings.pi_runtime_timeout_seconds,
        )
    except TimeoutError as error:
        process.kill()
        await process.wait()
        raise PiRuntimeError("Pi runtime timed out") from error
    if process.returncode != 0:
        raise PiRuntimeError(stderr.decode().strip() or "Pi runtime exited unsuccessfully")
    messages = [json.loads(line) for line in stdout.decode().splitlines() if line.strip()]
    error_message = next((message for message in messages if message["type"] == "error"), None)
    if error_message:
        raise PiRuntimeError(str(error_message["payload"].get("error", "Pi runtime error")))
    proposal = next((message for message in messages if message["type"] == "proposal"), None)
    if proposal is None:
        raise PiRuntimeError("Pi runtime produced no proposal")
    return proposal["payload"]
