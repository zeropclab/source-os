import { Agent } from "@earendil-works/pi-agent-core";
import { createInterface } from "node:readline";
import { PROTOCOL_VERSION, parseEnvelope, type StartEnvelope } from "./protocol.js";

void Agent;

type Outbound = {
  protocol_version: string;
  agent_run_id: string;
  sequence: number;
  type: "ready" | "error";
  payload: Record<string, unknown>;
};

function emit(message: Outbound): void {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

function handleStart(envelope: StartEnvelope): void {
  emit({
    protocol_version: PROTOCOL_VERSION,
    agent_run_id: envelope.agent_run_id,
    sequence: envelope.sequence,
    type: "ready",
    payload: {
      runtime: "pi-agent-core",
      pi_agent_core_loaded: true,
      evidence_bundle_hash: envelope.payload.evidence_bundle_hash,
      tool_policy: "SourceOS-controlled; no direct domain writes",
      provider_configured: Boolean(process.env.SOURCEOS_PI_PROVIDER),
    },
  });
}

const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of input) {
  try {
    handleStart(parseEnvelope(line));
  } catch (error) {
    emit({
      protocol_version: PROTOCOL_VERSION,
      agent_run_id: "unknown",
      sequence: 0,
      type: "error",
      payload: { error: error instanceof Error ? error.message : "Unknown protocol error" },
    });
  }
}
