import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const agentsRoot = path.dirname(fileURLToPath(import.meta.url));
const source = path.join(agentsRoot, "knowledge", "arbor3d-qa-1000.jsonl");
const outputFolder = path.join(agentsRoot, "fine-tuning", "data");
const system = [
  "你是 Arbor3D 樹木盤點助理，使用繁體中文回答。",
  "只能依據盤點規範回答，不得捏造真實量測、模型精度、健康診斷或碳權結論。",
  "資料不足時應明確指出待補證據與人工複核步驟。",
].join("");

const sourceRecords = fs.readFileSync(source, "utf8")
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => JSON.parse(line));

if (sourceRecords.length !== 1000) {
  throw new Error(`Expected 1000 records, received ${sourceRecords.length}`);
}

const records = sourceRecords.map((record) => ({
  id: record.id,
  category: record.category,
  messages: [
    { role: "system", content: system },
    { role: "user", content: record.question },
    { role: "assistant", content: record.answer },
  ],
}));

// 每個類別固定保留最後 5 題，共 100 題；避免拿訓練題評估模型。
const byCategory = Map.groupBy(records, (record) => record.category);
const train = [];
const evaluation = [];
for (const items of byCategory.values()) {
  train.push(...items.slice(0, -5));
  evaluation.push(...items.slice(-5));
}

const write = (name, values) => fs.writeFileSync(
  path.join(outputFolder, name),
  `${values.map((value) => JSON.stringify(value)).join("\n")}\n`,
  "utf8",
);

fs.mkdirSync(outputFolder, { recursive: true });
write("phi4-sft-all-1000.jsonl", records);
write("phi4-sft-train-900.jsonl", train);
write("phi4-sft-eval-100.jsonl", evaluation);
console.log(`Wrote ${train.length} train and ${evaluation.length} evaluation records to ${outputFolder}`);
