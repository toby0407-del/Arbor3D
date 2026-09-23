/** Generate explicitly labelled demo media for every simulated inventory. */
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(here, "..");
const inventoryRoot = path.join(appRoot, "src", "data", "inventories");
const publicRoot = path.join(appRoot, "public", "scans");
const notice = "樹表數值與三類技術影像均為可重建的合成展示資料，不代表目前地點的現場量測。";
const evidenceRoot = "../_shared/synthetic-tree-evidence";

function evidenceVariant(scanId, treeId, salt) {
  const input = `${salt}:${scanId}:${treeId}`;
  let seed = 2166136261;
  for (const char of input) {
    seed ^= char.charCodeAt(0);
    seed = Math.imul(seed, 16777619) >>> 0;
  }
  return String((seed % 4) + 1).padStart(2, "0");
}

function demoPly(scanId) {
  let seed = [...scanId].reduce((sum, char) => (sum * 33 + char.charCodeAt(0)) >>> 0, 5381);
  const random = () => {
    seed = (1664525 * seed + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  const rows = [];
  for (let level = 0; level < 45; level += 1) {
    const z = level * 0.12;
    const radius = 0.26 + Math.sin(level * 0.7) * 0.018;
    for (let side = 0; side < 20; side += 1) {
      const angle = (Math.PI * 2 * side) / 20 + (random() - 0.5) * 0.04;
      rows.push(`${(Math.cos(angle) * radius).toFixed(5)} ${(Math.sin(angle) * radius).toFixed(5)} ${(z + (random() - 0.5) * 0.025).toFixed(5)} 122 83 55`);
    }
  }
  return `ply\nformat ascii 1.0\ncomment SIMULATED DEMO - NOT FIELD EVIDENCE\nelement vertex ${rows.length}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n${rows.join("\n")}\n`;
}

const files = (await fs.readdir(inventoryRoot)).filter((name) => /^sim.*\.json$/i.test(name));
for (const file of files) {
  const source = path.join(inventoryRoot, file);
  const report = JSON.parse(await fs.readFile(source, "utf8"));
  const scanId = String(report.scan_id || path.basename(file, ".json"));
  if (!scanId.startsWith("sim")) throw new Error(`Refusing to modify non-simulated scan: ${scanId}`);
  report.dataset_kind = "simulated";
  report.simulation_notice = report.simulation_reference
    ? `四年季度、1.3 m 人工胸徑、樹高、固定樹號與 GPS/GPX 均為模擬。${notice}`
    : notice;
  report.simulation_media_source = "Arbor3D 合成展示素材庫（樹幹分割、胸高橫切面、點雲側視）";
  for (const [index, tree] of (report.trees || []).entries()) {
    const treeKey = String(tree.Tree_ID || index);
    tree.DBH_note = String(tree.DBH_note || "").includes("模擬")
      ? tree.DBH_note
      : `模擬資料,${tree.DBH_note || "no_measurement"}`;
    delete tree.Best_Photo;
    tree.Mask_Path = `${evidenceRoot}/masks/mask-${evidenceVariant(scanId, treeKey, "mask")}.png`;
    tree.Cross_Section_Image = `${evidenceRoot}/cross-sections/cross-section-${evidenceVariant(scanId, treeKey, "cross")}.png`;
    tree.PointCloud_Preview = `${evidenceRoot}/point-clouds/point-cloud-${evidenceVariant(scanId, treeKey, "cloud")}.png`;
    tree["3D_Model_Path"] = "simulated-demo/tree-demo.ply";
    tree.Single_Tree_Ply = "simulated-demo/tree-demo.ply";
  }
  const rendered = `${JSON.stringify(report, null, 2)}\n`;
  await fs.writeFile(source, rendered, "utf8");
  const scanRoot = path.join(publicRoot, scanId);
  const mediaRoot = path.join(scanRoot, "simulated-demo");
  await fs.mkdir(mediaRoot, { recursive: true });
  await fs.writeFile(path.join(scanRoot, "inventory.json"), rendered, "utf8");
  for (const legacy of ["photo.svg", "mask.svg", "cross-section.svg", "point-cloud-preview.svg"]) {
    await fs.rm(path.join(mediaRoot, legacy), { force: true });
  }
  await fs.writeFile(path.join(mediaRoot, "tree-demo.ply"), demoPly(scanId), "utf8");
}
console.log(`Generated explicitly labelled simulated media for ${files.length} inventories.`);
