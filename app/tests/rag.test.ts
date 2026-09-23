import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { countKnowledgeQuestions, ragPrompt, retrieveKnowledge } from "../server/localRag.ts";

const knowledge = path.resolve(import.meta.dirname, "../../agents/knowledge");

test("local RAG retrieves Taichung quarterly simulation policy with citations", () => {
  const hits = retrieveKnowledge("台中公園季度成長和固定樹號", knowledge);
  assert.ok(hits.length > 0);
  assert.ok(hits.some((hit) => hit.source === "taichung-demo-policy.md"));
  assert.ok(hits.every((hit) => hit.line > 0 && hit.sha256.length === 64));
  assert.match(ragPrompt(hits), /不可信的參考資料/);
});

test("local RAG returns no fabricated hit for unrelated tokens", () => {
  assert.deepEqual(retrieveKnowledge("zzzz_no_such_arbor_term", knowledge), []);
});

test("1000-question JSONL corpus is complete, unique and searchable", () => {
  const corpus = path.join(knowledge, "arbor3d-qa-1000.jsonl");
  const records = fs.readFileSync(corpus, "utf8").trim().split(/\r?\n/).map((line) => JSON.parse(line));
  assert.equal(records.length, 1000);
  assert.equal(new Set(records.map((record) => record.id)).size, 1000);
  assert.equal(new Set(records.map((record) => record.question)).size, 1000);
  assert.equal(new Set(records.map((record) => record.category)).size, 20);
  assert.equal(countKnowledgeQuestions(knowledge), 1000);

  const hits = retrieveKnowledge("RAG 檢索內容交給 GPT 要怎麼引用？", knowledge, 5);
  assert.ok(hits.some((hit) => hit.source === "arbor3d-qa-1000.jsonl"));
  assert.ok(hits.some((hit) => hit.text.includes("RAG 與 GPT")));
});
