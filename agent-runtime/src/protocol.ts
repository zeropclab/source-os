export const PROTOCOL_VERSION = "1.0";

export type StartEnvelope = {
  protocol_version: string;
  message_id: string;
  agent_run_id: string;
  sequence: number;
  type: "start";
  payload: {
    evidence_bundle_hash: string;
    budget: {
      max_tool_calls: number;
      max_tokens: number;
      max_cost_cents: number;
    };
  };
};

export type RuntimeEnvelope = StartEnvelope;

export function parseEnvelope(line: string): RuntimeEnvelope {
  const parsed: unknown = JSON.parse(line);
  if (typeof parsed !== "object" || parsed === null) throw new Error("Protocol envelope must be an object");
  const envelope = parsed as Partial<StartEnvelope>;
  if (envelope.protocol_version !== PROTOCOL_VERSION) {
    throw new Error(`Unsupported protocol version: ${String(envelope.protocol_version)}`);
  }
  if (envelope.type !== "start" || !envelope.agent_run_id || !envelope.message_id) {
    throw new Error("Only a fully identified start envelope is accepted");
  }
  return envelope as StartEnvelope;
}
