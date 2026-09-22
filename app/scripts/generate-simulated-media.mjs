/** Generate explicitly labelled demo media for every simulated inventory. */
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(here, "..");
const inventoryRoot = path.join(appRoot, "src", "data", "inventories");
const publicRoot = path.join(appRoot, "public", "scans");
const observedScanId = "20260818092855";
const notice = "樹表數值仍為合成；四格影像借用逢甲大學實拍照片與 2026-08-18 真實掃描成果，僅供跨地點介面模擬，不代表目前地點的現場資料。";
const sharedPhoto = path.join(publicRoot, "_shared", "fengchia-field", "field-photo.jpg");
const fieldPhotoSource = process.env.ARBOR3D_FENGCHIA_PHOTO || path.join(os.homedir(), "Downloads", "image.jpg");

await fs.mkdir(path.dirname(sharedPhoto), { recursive: true });
try {
  await fs.copyFile(fieldPhotoSource, sharedPhoto);
} catch (error) {
  try {
    await fs.access(sharedPhoto);
  } catch {
    throw new Error(`找不到逢甲實拍照片：${fieldPhotoSource}`, { cause: error });
  }
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
  report.simulation_media_source = "逢甲大學實拍照片 + 真實掃描 20260818092855（Tree_001～Tree_016）";
  for (const [index, tree] of (report.trees || []).entries()) {
    const sourceNumber = String((index % 16) + 1).padStart(3, "0");
    const sourceTree = `Tree_${sourceNumber}`;
    tree.DBH_note = String(tree.DBH_note || "").includes("模擬")
      ? tree.DBH_note
      : `模擬資料,${tree.DBH_note || "no_measurement"}`;
    tree.Best_Photo = "../_shared/fengchia-field/field-photo.jpg";
    tree.Mask_Path = `../${observedScanId}/masks/real_tree_mask_${sourceTree}.png`;
    tree.Cross_Section_Image = `../${observedScanId}/dbh/dbh_slice_top_down_${sourceTree}.png`;
    tree.PointCloud_Preview = `../${observedScanId}/previews/${sourceTree}.png`;
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
