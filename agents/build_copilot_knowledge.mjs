import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const agentsRoot = path.dirname(fileURLToPath(import.meta.url));
const source = path.join(agentsRoot, "knowledge", "arbor3d-qa-1000.jsonl");
const outputFolder = path.join(agentsRoot, "copilot-upload");
const output = path.join(outputFolder, "Arbor3D-RAG-1000.md");

const records = fs.readFileSync(source, "utf8")
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => JSON.parse(line));

if (records.length !== 1000) {
  throw new Error(`Expected 1000 knowledge records, received ${records.length}`);
}

const grouped = Map.groupBy(records, (record) => record.category);
const lines = [
  "# Arbor3D Copilot RAG 知識包",
  "",
  "> 用途：上傳至 Microsoft Copilot Studio 的 Knowledge，讓 Arbor3D Copilot 以受控盤點規範回答。",
  "> 本檔是領域知識與問答規則，不是 1,000 筆現場觀測，也不可取代人工複核。",
  "",
  `共 ${records.length} 題，${grouped.size} 類。`,
  "",
];

for (const [category, items] of grouped) {
  lines.push(`## ${category}`, "");
  for (const item of items) {
    lines.push(
      `### ${item.id}`,
      "",
      `問題：${item.question}`,
      "",
      `答案：${item.answer}`,
      "",
      `關鍵字：${item.keywords.join("、")}`,
      "",
    );
  }
}

fs.mkdirSync(outputFolder, { recursive: true });
fs.writeFileSync(output, `${lines.join("\n")}\n`, "utf8");
console.log(`Wrote ${records.length} questions to ${output}`);
