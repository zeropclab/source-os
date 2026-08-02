import { Agent } from "@earendil-works/pi-agent-core";
import { contentText, type Model, type StreamFunction } from "@earendil-works/pi-ai";
import { builtinModels } from "@earendil-works/pi-ai/providers/all";
import { fauxAssistantMessage, fauxProvider } from "@earendil-works/pi-ai/providers/faux";
import { createInterface } from "node:readline";

import { PROTOCOL_VERSION, parseEnvelope, type StartEnvelope } from "./protocol.js";

type Outbound = {
  protocol_version: string;
  agent_run_id: string;
  sequence: number;
  type: "ready" | "proposal" | "error";
  payload: Record<string, unknown>;
};

function emit(message: Outbound): void {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

function systemPrompt(envelope: StartEnvelope): string {
  return [
    "You are SourceOS's proposal-only evidence analyst.",
    "You may not assert validation, market size, willingness to pay, or business decisions.",
    "You have no tools and may not alter any external system.",
    `Citations allowed in this bounded run: ${envelope.payload.citations.join(", ")}.`,
    `Bounded evidence bundle: ${JSON.stringify(envelope.payload.evidence_bundle)}.`,
    "Return a concise need hypothesis, competing explanation, unknowns, and smallest validation action.",
  ].join("\n");
}

function fauxStream(envelope: StartEnvelope): { model: Model<any>; streamFn: StreamFunction<any> } {
  const faux = fauxProvider({
    provider: "faux",
    models: [{ id: envelope.payload.model, name: envelope.payload.model }],
  });
  faux.setResponses([
    fauxAssistantMessage(
      JSON.stringify({
        kind: "need_issue_proposal",
        proposed_status: "captured",
        citations: envelope.payload.citations,
        cannot_conclude: "Faux execution is a runtime contract test, not market evidence.",
      }),
    ),
  ]);
  return {
    model: faux.getModel(),
    streamFn: (model, context, options) => faux.provider.streamSimple(model, context, options),
  };
}

function configuredStream(envelope: StartEnvelope): { model: Model<any>; streamFn: StreamFunction<any> } {
  if (envelope.payload.provider === "faux") return fauxStream(envelope);
  const models = builtinModels();
  const model = models.getModel(envelope.payload.provider, envelope.payload.model);
  if (!model) {
    throw new Error(
      `Configured Pi model not found: ${envelope.payload.provider}/${envelope.payload.model}`,
    );
  }
  return { model, streamFn: models.streamSimple.bind(models) };
}

async function runProposal(envelope: StartEnvelope): Promise<Record<string, unknown>> {
  const { model, streamFn } = configuredStream(envelope);
  const agent = new Agent({
    initialState: { model, systemPrompt: systemPrompt(envelope), tools: [] },
    streamFn,
    beforeToolCall: async () => ({
      block: true,
      reason: "SourceOS proposal runs have no executable tools.",
    }),
  });
  await agent.prompt(envelope.payload.task_instruction);
  const assistant = [...agent.state.messages].reverse().find((message) => message.role === "assistant");
  if (!assistant || assistant.role !== "assistant") {
    throw new Error(agent.state.errorMessage || "Pi Agent returned no assistant message");
  }
  const costCents = Math.ceil(assistant.usage.cost.total * 100);
  if (assistant.usage.totalTokens > envelope.payload.budget.max_tokens) {
    throw new Error("Pi Agent exceeded the configured token budget");
  }
  if (costCents > envelope.payload.budget.max_cost_cents) {
    throw new Error("Pi Agent exceeded the configured cost budget");
  }
  return {
    provider: envelope.payload.provider,
    model: envelope.payload.model,
    citations: envelope.payload.citations,
    raw_output: contentText(assistant.content),
    usage: { tokens: assistant.usage.totalTokens, cost_cents: costCents },
    tool_policy: "no executable tools",
    cannot_conclude: "This is a proposal requiring operator review and real validation.",
  };
}

async function handleStart(envelope: StartEnvelope): Promise<void> {
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
      provider: envelope.payload.provider,
      model: envelope.payload.model,
    },
  });
  const proposal = await runProposal(envelope);
  emit({
    protocol_version: PROTOCOL_VERSION,
    agent_run_id: envelope.agent_run_id,
    sequence: envelope.sequence + 1,
    type: "proposal",
    payload: proposal,
  });
}

const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of input) {
  try {
    await handleStart(parseEnvelope(line));
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
