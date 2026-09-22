/** Generate explicitly labelled demo media for every simulated inventory. */
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(here, "..");
const inventoryRoot = path.join(appRoot, "src", "data", "inventories");
const publicRoot = path.join(appRoot, "public", "scans");
const notice = "合成樹表、合成媒體與示意點雲；僅供功能展示，不代表現場影像、實測 DBH、GPS 或模型精度。";

function escapeXml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function svg(scanId, kind, subtitle, drawing) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
  <rect width="960" height="540" fill="#142018"/>
  <rect x="24" y="24" width="912" height="492" rx="24" fill="#edf3e8" stroke="#dc8a26" stroke-width="6"/>
  <rect x="48" y="48" width="864" height="58" rx="12" fill="#fff0d2"/>
  <text x="70" y="86" font-family="sans-serif" font-size="28" font-weight="700" fill="#8a4300">DEMO · SIMULATED · 非現場證據</text>
  ${drawing}
  <text x="480" y="448" text-anchor="middle" font-family="sans-serif" font-size="30" font-weight="700" fill="#23422c">${escapeXml(kind)}</text>
  <text x="480" y="481" text-anchor="middle" font-family="sans-serif" font-size="18" fill="#506453">${escapeXml(subtitle)}</text>
  <text x="480" y="505" text-anchor="middle" font-family="monospace" font-size="15" fill="#7a887b">${escapeXml(scanId)}</text>
</svg>\n`;
}

function demoSvgs(scanId) {
  const tree = `<ellipse cx="480" cy="397" rx="180" ry="22" fill="#c8d4c4"/>
  <path d="M438 385 C450 310 440 230 462 142 L505 142 C525 238 510 318 526 385 Z" fill="#74513a"/>
  <circle cx="430" cy="200" r="82" fill="#4b7d4e"/><circle cx="520" cy="185" r="92" fill="#568f57"/><circle cx="585" cy="230" r="65" fill="#477849"/>`;
  const mask = `${tree}<path d="M438 385 C450 310 440 230 462 142 L505 142 C525 238 510 318 526 385 Z" fill="#e94f37" opacity=".78" stroke="#fff" stroke-width="5"/>`;
  const cross = `<circle cx="480" cy="270" r="125" fill="none" stroke="#607567" stroke-width="3" stroke-dasharray="8 8"/>
  <circle cx="480" cy="270" r="88" fill="#9b704f" stroke="#4f3424" stroke-width="10"/>
  <line x1="392" y1="270" x2="568" y2="270" stroke="#ed5b43" stroke-width="8"/><text x="480" y="255" text-anchor="middle" font-family="sans-serif" font-size="22" fill="#fff">示意 DBH</text>`;
  const cloud = Array.from({ length: 90 }, (_, i) => {
    const angle = i * 2.39996;
    const radius = 25 + (i % 13) * 8;
    const x = 480 + Math.cos(angle) * radius;
    const y = 285 + Math.sin(angle) * radius * 0.72;
    return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.2" fill="#${i % 4 === 0 ? "dc8a26" : "477849"}"/>`;
  }).join("");
  return {
    "photo.svg": svg(scanId, "合成影像佔位", "沒有宣稱為現場照片", tree),
    "mask.svg": svg(scanId, "合成 Segmentation 佔位", "沒有執行真實 YOLO 推論", mask),
    "cross-section.svg": svg(scanId, "合成胸高橫切面", "不是 1.3 m 現場實測", cross),
    "point-cloud-preview.svg": svg(scanId, "合成點雲側視", "僅測試媒體與 3D 載入流程", cloud),
  };
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
  report.simulation_notice = notice;
  for (const tree of report.trees || []) {
    tree.DBH_note = String(tree.DBH_note || "").includes("模擬")
      ? tree.DBH_note
      : `模擬資料,${tree.DBH_note || "no_measurement"}`;
    tree.Best_Photo = "simulated-demo/photo.svg";
    tree.Mask_Path = "simulated-demo/mask.svg";
    tree.Cross_Section_Image = "simulated-demo/cross-section.svg";
    tree.PointCloud_Preview = "simulated-demo/point-cloud-preview.svg";
    tree["3D_Model_Path"] = "simulated-demo/tree-demo.ply";
    tree.Single_Tree_Ply = "simulated-demo/tree-demo.ply";
  }
  const rendered = `${JSON.stringify(report, null, 2)}\n`;
  await fs.writeFile(source, rendered, "utf8");
  const scanRoot = path.join(publicRoot, scanId);
  const mediaRoot = path.join(scanRoot, "simulated-demo");
  await fs.mkdir(mediaRoot, { recursive: true });
  await fs.writeFile(path.join(scanRoot, "inventory.json"), rendered, "utf8");
  for (const [name, content] of Object.entries(demoSvgs(scanId))) {
    await fs.writeFile(path.join(mediaRoot, name), content, "utf8");
  }
  await fs.writeFile(path.join(mediaRoot, "tree-demo.ply"), demoPly(scanId), "utf8");
}
console.log(`Generated explicitly labelled simulated media for ${files.length} inventories.`);
