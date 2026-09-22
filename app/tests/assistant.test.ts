import assert from "node:assert/strict";
import test from "node:test";
import { localAssistantReply, type AssistantContext } from "../server/assistantCore.ts";

const context: AssistantContext = {
  parkName: "逢甲大學",
  pathName: "測試路徑",
  scanId: "scan-1",
  createdAt: "2026-08-18T09:00:00+08:00",
  summary: { total: 2, reliable: 1, pending: 0, review: 1, co2Ton: 1.25 },
  trees: [
    {
      id: "Tree_001",
      dbhCm: 20,
      heightM: 8,
      co2Ton: 0.45,
      status: "green",
      reviewReason: "",
      confidence: 0.9,
      manualDbhCm: null,
    },
    {
      id: "Tree_002",
      dbhCm: 50,
      heightM: 12,
      co2Ton: 0.8,
      status: "red",
      reviewReason: "卡尺偏寬待複核",
      confidence: 0.5,
      manualDbhCm: null,
    },
  ],
};

test("local assistant names review trees from evidence", () => {
  const reply = localAssistantReply("哪些樹需要優先複核？", context);
  assert.equal(reply.provider, "local");
  assert.match(reply.answer, /Tree_002/);
  assert.doesNotMatch(reply.answer, /Tree_003/);
});

test("local assistant refuses to invent accuracy without manual pairs", () => {
  const reply = localAssistantReply("AI 準確率是多少？", context);
  assert.match(reply.answer, /還不能宣稱/);
  assert.ok(reply.evidence.some((item) => item.includes("0 筆")));
});

test("local assistant labels carbon as an estimate", () => {
  const reply = localAssistantReply("碳匯是多少？", context);
  assert.match(reply.answer, /1\.25 ton/);
  assert.match(reply.answer, /估算/);
  assert.match(reply.answer, /不應作為正式碳權/);
});
