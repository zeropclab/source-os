import assert from "node:assert/strict";
import test from "node:test";

import { parseEnvelope, PROTOCOL_VERSION } from "../dist/protocol.js";

const start = {
  protocol_version: PROTOCOL_VERSION,
  message_id: "m-1",
  agent_run_id: "ar-1",
  sequence: 1,
  type: "start",
  payload: {
    evidence_bundle_hash: "abc",
    task_instruction: "Draft a proposal only.",
    citations: ["signal-1"],
    evidence_bundle: [{ signal_id: "signal-1", observation: "Manual workaround." }],
    provider: "faux",
    model: "sourceos-proposal-faux-v1",
    budget: { max_tool_calls: 2, max_tokens: 100, max_cost_cents: 1 },
  },
};

test("accepts a fully identified start envelope", () => {
  assert.deepEqual(parseEnvelope(JSON.stringify(start)), start);
});

test("rejects an unsupported protocol version", () => {
  assert.throws(
    () => parseEnvelope(JSON.stringify({ ...start, protocol_version: "9.9" })),
    /Unsupported protocol version/,
  );
});
