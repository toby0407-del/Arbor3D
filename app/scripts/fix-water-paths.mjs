import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const bindingsPath = path.join(root, "src", "data", "scanBindings.ts");

function mulberry32(a) {
  return function () {
    let t = (a += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** landSign: Local_XYZ X 取此方向，讓樹留在陸側 */
const byScan = {
  sim20260329qhg001: {
    pathName: "北側高架步道",
    // 谷頂北側陸域（臺灣大道側），全程在水池以北
    polyline: [
      [24.16848, 120.6384],
      [24.1685, 120.6387],
      [24.16852, 120.639],
      [24.16854, 120.6393],
      [24.16856, 120.6396],
      [24.16858, 120.6399],
    ],
    landSign: 1,
  },
  sim20260327tcp001: {
    pathName: "日月湖東岸轉彎",
    polyline: [
      [24.1429, 120.68505],
      [24.14315, 120.68515],
      [24.14345, 120.6852],
      [24.14375, 120.68518],
      [24.14405, 120.6851],
      [24.1443, 120.6849],
      [24.14445, 120.6846],
    ],
    landSign: -1,
  },
  sim20260330wxf001: {
    pathName: "北緣園道",
    polyline: [
      [24.14615, 120.6441],
      [24.14618, 120.6444],
      [24.1462, 120.6447],
      [24.14622, 120.645],
      [24.14625, 120.6453],
      [24.14628, 120.6456],
    ],
    landSign: 1,
  },
  sim20260328flp001: {
    pathName: "南側園道",
    polyline: [
      [24.13005, 120.6419],
      [24.13008, 120.6422],
      [24.1301, 120.6425],
      [24.13012, 120.6428],
      [24.13015, 120.6431],
      [24.13018, 120.6434],
    ],
    landSign: -1,
  },
  sim20260402tcc001: {
    pathName: "中央公園大道東側",
    polyline: [
      [24.1854, 120.65455],
      [24.1857, 120.65458],
      [24.186, 120.6546],
      [24.1863, 120.65462],
      [24.1866, 120.65465],
      [24.1869, 120.65468],
    ],
    landSign: 1,
  },
  sim20260401tcm001: {
    pathName: "東側主園道",
    polyline: [
      [24.2084, 120.59825],
      [24.2082, 120.59828],
      [24.208, 120.5983],
      [24.2078, 120.59832],
      [24.2076, 120.59835],
      [24.2074, 120.59838],
    ],
    landSign: 1,
  },
};

let text = fs.readFileSync(bindingsPath, "utf8");

for (const [scanId, fix] of Object.entries(byScan)) {
  const marker = `scanId: "${scanId}"`;
  const start = text.indexOf(marker);
  if (start < 0) {
    console.error("missing binding", scanId);
    continue;
  }

  const nameStart = text.lastIndexOf("pathName:", start);
  const nameLineEnd = text.indexOf("\n", nameStart);
  text =
    text.slice(0, nameStart) +
    `pathName: "${fix.pathName}"` +
    text.slice(nameLineEnd);

  const scanAt = text.indexOf(marker);
  const polyStart = text.indexOf("polyline: [", scanAt);
  const polyEnd = text.indexOf("],", polyStart) + 2;
  const poly =
    "polyline: [\n" +
    fix.polyline.map(([a, b]) => `      [${a}, ${b}],`).join("\n") +
    "\n    ]";
  text = text.slice(0, polyStart) + poly + text.slice(polyEnd);

  const invPath = path.join(root, "src", "data", "inventories", `${scanId}.json`);
  const inv = JSON.parse(fs.readFileSync(invPath, "utf8"));
  const seed = [...scanId].reduce((a, c) => a + c.charCodeAt(0), 0);
  const rand = mulberry32(seed);
  inv.trees.forEach((tree, i) => {
    const along =
      -38 + (i / Math.max(1, inv.trees.length - 1)) * 72 + (rand() - 0.5) * 2;
    const side = fix.landSign * (0.8 + rand() * 1.6);
    tree.Local_XYZ_m = [
      +side.toFixed(3),
      +along.toFixed(3),
      tree.Local_XYZ_m[2],
    ];
  });
  fs.writeFileSync(invPath, `${JSON.stringify(inv, null, 2)}\n`);
  console.log("fixed", scanId, fix.pathName);
}

fs.writeFileSync(bindingsPath, text);
console.log("done");
