import assert from "node:assert/strict";
import test from "node:test";
import { askCopilotStudio, askPhi4Cloud, askPhi4Local } from "../server/assistantApiPlugin.ts";
import type { AssistantContext } from "../server/assistantCore.ts";

const context: AssistantContext = {
  parkName: "逢甲大學",
  pathName: "測試路徑",
  scanId: "scan-1",
  createdAt: "2026-08-18T09:00:00+08:00",
  summary: { total: 1, reliable: 1, pending: 0, review: 0, co2Ton: 0.45 },
  trees: [{
    id: "Tree_001",
    dbhCm: 20,
    heightM: 8,
    co2Ton: 0.45,
    status: "green",
    reviewReason: "",
    confidence: 0.9,
    manualDbhCm: null,
  }],
};

test("Copilot Studio adapter uses server-side Direct Line and returns the agent answer", { concurrency: false }, async () => {
  const originalFetch = globalThis.fetch;
  const calls: Array<{ url: string; method: string; body?: string }> = [];
  globalThis.fetch = async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    calls.push({ url, method, body: typeof init?.body === "string" ? init.body : undefined });
    if (url === "https://example.test/copilot-token") {
      return Response.json({ token: "direct-line-token", conversationId: "conversation-1" });
    }
    if (method === "POST") return Response.json({ id: "activity-1" });
    return Response.json({
      activities: [{
        type: "message",
        from: { id: "copilot-agent", name: "Arbor3D Copilot" },
        text: "請優先複核 Tree_001。",
      }],
    });
  };

  try {
    const reply = await askCopilotStudio("今天先做什麼？", context, {
      COPILOT_STUDIO_TOKEN_ENDPOINT: "https://example.test/copilot-token",
      COPILOT_STUDIO_AGENT_NAME: "Arbor3D Copilot",
      ARBOR_ALLOW_BILLABLE_CLOUD: "YES_I_ACCEPT_COSTS",
    }, []);
    assert.equal(reply?.provider, "copilot");
    assert.equal(reply?.model, "Arbor3D Copilot");
    assert.equal(reply?.answer, "請優先複核 Tree_001。");
    assert.equal(calls.length, 3);
    assert.match(calls[1].body ?? "", /今天先做什麼/);
    assert.ok(!calls[0].url.includes("direct-line-token"));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Copilot Studio adapter stays disabled without an endpoint", async () => {
  const reply = await askCopilotStudio("測試", context, {
    ARBOR_ALLOW_BILLABLE_CLOUD: "YES_I_ACCEPT_COSTS",
  }, []);
  assert.equal(reply, null);
});

test("Phi-4 adapter sends RAG-grounded requests only to loopback", { concurrency: false }, async () => {
  const originalFetch = globalThis.fetch;
  let requestBody = "";
  globalThis.fetch = async (_input, init) => {
    requestBody = typeof init?.body === "string" ? init.body : "";
    return Response.json({
      choices: [{ message: { content: "請先完成標準胸高人工量測。" } }],
    });
  };
  try {
    const reply = await askPhi4Local("下一步？", context, {
      FOUNDRY_LOCAL_ENDPOINT: "http://127.0.0.1:5272",
      FOUNDRY_LOCAL_MODEL: "phi-4-mini",
    }, [{ source: "measurement-policy.md", line: 3, text: "胸高 1.3 公尺" }]);
    assert.equal(reply?.provider, "phi4");
    assert.equal(reply?.model, "phi-4-mini");
    assert.match(requestBody, /measurement-policy\.md/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Phi-4 adapter rejects non-loopback endpoints", async () => {
  await assert.rejects(
    askPhi4Local("測試", context, {
      FOUNDRY_LOCAL_ENDPOINT: "https://untrusted.example.test",
    }, []),
    /只允許本機 loopback/,
  );
});

test("Phi-4 cloud adapter uses HTTPS, RAG and a server-side key", { concurrency: false }, async () => {
  const originalFetch = globalThis.fetch;
  let calledUrl = "";
  let requestBody = "";
  let requestHeaders: HeadersInit | undefined;
  globalThis.fetch = async (input, init) => {
    calledUrl = String(input);
    requestBody = typeof init?.body === "string" ? init.body : "";
    requestHeaders = init?.headers;
    return Response.json({ choices: [{ message: { content: "雲端 Phi-4 回答" } }] });
  };
  try {
    const reply = await askPhi4Cloud("下一步？", context, {
      PHI4_CLOUD_ENDPOINT: "https://arbor3d.services.ai.azure.com/openai/v1",
      PHI4_CLOUD_MODEL: "Phi-4-mini-instruct",
      PHI4_CLOUD_API_KEY: "server-only-test-key",
      ARBOR_ALLOW_BILLABLE_CLOUD: "YES_I_ACCEPT_COSTS",
    }, [{ source: "measurement-policy.md", line: 3, text: "胸高 1.3 公尺" }]);
    assert.equal(reply?.provider, "phi4");
    assert.match(reply?.model ?? "", /Azure/);
    assert.equal(calledUrl, "https://arbor3d.services.ai.azure.com/openai/v1/chat/completions");
    assert.match(requestBody, /measurement-policy\.md/);
    assert.equal((requestHeaders as Record<string, string>)["api-key"], "server-only-test-key");
    assert.doesNotMatch(requestBody, /server-only-test-key/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("assistant status stays local until token and billable lock are set", async () => {
  const { assistantProviderStatus } = await import("../server/assistantApiPlugin.ts");
  const locked = assistantProviderStatus({
    ARBOR_AI_PROVIDER: "copilot",
    ARBOR_ALLOW_BILLABLE_CLOUD: "NO",
  });
  assert.equal(locked.activeMode, "local");
  assert.equal(locked.copilotConfigured, false);
  const ready = assistantProviderStatus({
    ARBOR_AI_PROVIDER: "copilot",
    COPILOT_STUDIO_TOKEN_ENDPOINT: "https://example.test/token",
    ARBOR_ALLOW_BILLABLE_CLOUD: "YES_I_ACCEPT_COSTS",
  });
  assert.equal(ready.activeMode, "copilot");
  assert.equal(ready.copilotConfigured, true);
  const phi4 = assistantProviderStatus({
    ARBOR_AI_PROVIDER: "phi4",
    FOUNDRY_LOCAL_ENDPOINT: "http://127.0.0.1:5272",
  });
  assert.equal(phi4.activeMode, "phi4");
  assert.equal(phi4.phi4Configured, true);
  const phi4Cloud = assistantProviderStatus({
    ARBOR_AI_PROVIDER: "phi4-cloud",
    PHI4_CLOUD_ENDPOINT: "https://example.services.ai.azure.com/openai/v1",
    PHI4_CLOUD_MODEL: "Phi-4-mini-instruct",
    ARBOR_ALLOW_BILLABLE_CLOUD: "YES_I_ACCEPT_COSTS",
  });
  assert.equal(phi4Cloud.activeMode, "phi4-cloud");
  assert.equal(phi4Cloud.phi4CloudConfigured, true);
});
