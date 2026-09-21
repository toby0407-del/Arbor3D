import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const invDir = path.join(root, "src", "data", "inventories");

function mulberry32(a) {
  return function () {
    let t = (a += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** 有水域風險的公園：側向只留 0.6–1.4 m，緊貼轉彎步道 */
const hugPath = new Set([
  "sim20260327tcp001",
  "sim20260328flp001",
  "sim20260329qhg001",
  "sim20260330wxf001",
  "sim20260401tcm001",
  "sim20260402tcc001",
]);

for (const name of fs.readdirSync(invDir)) {
  if (!name.startsWith("sim") || !name.endsWith(".json")) continue;
  const scanId = name.replace(/\.json$/, "");
  const file = path.join(invDir, name);
  const inv = JSON.parse(fs.readFileSync(file, "utf8"));
  const rand = mulberry32([...scanId].reduce((a, c) => a + c.charCodeAt(0), 0));
  const tight = hugPath.has(scanId);
  inv.trees.forEach((tree, i) => {
    const along =
      -38 + (i / Math.max(1, inv.trees.length - 1)) * 72 + (rand() - 0.5) * 2;
    const mag = tight ? 0.6 + rand() * 0.8 : 0.9 + rand() * 1.8;
    const side = (rand() > 0.5 ? 1 : -1) * mag;
    tree.Local_XYZ_m = [
      +side.toFixed(3),
      +along.toFixed(3),
      tree.Local_XYZ_m[2],
    ];
  });
  fs.writeFileSync(file, `${JSON.stringify(inv, null, 2)}\n`);
  console.log("hug", scanId, tight ? "tight" : "normal");
}
