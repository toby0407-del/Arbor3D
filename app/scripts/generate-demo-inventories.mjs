import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

/** 僅台中：parkName 須與 taiwan_sites.json 完全相同 */
const sites = [
  // universities / colleges（逢甲真實掃描另綁，這裡不重複）
  {
    parkName: "東海大學",
    pathId: "thu-campus-demo-20260315",
    pathName: "東海校園主軸（模擬）",
    scanId: "sim20260315thu001",
    center: [24.178883, 120.603483],
    trees: 20,
    seed: 301,
  },
  {
    parkName: "國立中興大學",
    pathId: "nchu-campus-demo-20260316",
    pathName: "中興校園環線（模擬）",
    scanId: "sim20260316nchu01",
    center: [24.120282, 120.676426],
    trees: 18,
    seed: 311,
  },
  {
    parkName: "靜宜大學",
    pathId: "pu-campus-demo-20260317",
    pathName: "靜宜校園步道（模擬）",
    scanId: "sim20260317pu0001",
    center: [24.2272, 120.580674],
    trees: 16,
    seed: 321,
  },
  {
    parkName: "亞洲大學",
    pathId: "asia-campus-demo-20260318",
    pathName: "亞大校園路徑（模擬）",
    scanId: "sim20260318asia01",
    center: [24.047397, 120.686808],
    trees: 15,
    seed: 331,
  },
  {
    parkName: "朝陽科技大學",
    pathId: "cyut-campus-demo-20260319",
    pathName: "朝陽校園環線（模擬）",
    scanId: "sim20260319cyut01",
    center: [24.068736, 120.714619],
    trees: 14,
    seed: 341,
  },
  {
    parkName: "中國醫藥大學",
    pathId: "cmu-campus-demo-20260320",
    pathName: "中國醫北區校區（模擬）",
    scanId: "sim20260320cmu001",
    center: [24.156546, 120.680324],
    trees: 14,
    seed: 351,
  },
  {
    parkName: "中山醫學大學",
    pathId: "csmu-campus-demo-20260321",
    pathName: "中山醫校園路徑（模擬）",
    scanId: "sim20260321csmu01",
    center: [24.122519, 120.650889],
    trees: 13,
    seed: 361,
  },
  {
    parkName: "國立臺中教育大學",
    pathId: "ntcu-campus-demo-20260322",
    pathName: "中教大校園（模擬）",
    scanId: "sim20260322ntcu01",
    center: [24.143568, 120.671784],
    trees: 12,
    seed: 371,
  },
  {
    parkName: "國立臺中科技大學三民校區",
    pathId: "nutc-campus-demo-20260323",
    pathName: "中科大三民校區（模擬）",
    scanId: "sim20260323nutc01",
    center: [24.150709, 120.683079],
    trees: 12,
    seed: 381,
  },
  {
    parkName: "國立勤益科技大學",
    pathId: "ncut-campus-demo-20260324",
    pathName: "勤益校園路徑（模擬）",
    scanId: "sim20260324ncut01",
    center: [24.145053, 120.730315],
    trees: 13,
    seed: 391,
  },
  {
    parkName: "弘光科技大學",
    pathId: "hk-campus-demo-20260325",
    pathName: "弘光校園步道（模擬）",
    scanId: "sim20260325hk0001",
    center: [24.217301, 120.582625],
    trees: 12,
    seed: 401,
  },
  {
    parkName: "僑光科技大學",
    pathId: "ocu-campus-demo-20260326",
    pathName: "僑光校園路徑（模擬）",
    scanId: "sim20260326ocu001",
    center: [24.188967, 120.644324],
    trees: 11,
    seed: 411,
  },
  // parks
  {
    parkName: "臺中公園",
    pathId: "tc-park-demo-20260327",
    pathName: "臺中公園湖心步道（模擬）",
    scanId: "sim20260327tcp001",
    center: [24.144312, 120.684053],
    trees: 22,
    seed: 421,
  },
  {
    parkName: "豐樂雕塑公園",
    pathId: "fengle-demo-20260328",
    pathName: "豐樂雕塑公園主軸（模擬）",
    scanId: "sim20260328flp001",
    center: [24.130802, 120.642658],
    trees: 18,
    seed: 431,
  },
  {
    parkName: "秋紅谷廣場",
    pathId: "qiuhonggu-demo-20260329",
    pathName: "秋紅谷廣場步道（模擬）",
    scanId: "sim20260329qhg001",
    center: [24.167374, 120.639055],
    trees: 16,
    seed: 441,
  },
  {
    parkName: "文心森林公園",
    pathId: "wenxin-forest-demo-20260330",
    pathName: "文心森林公園環線（模擬）",
    scanId: "sim20260330wxf001",
    center: [24.145316, 120.644907],
    trees: 20,
    seed: 451,
  },
  {
    parkName: "惠來公園",
    pathId: "huilai-demo-20260331",
    pathName: "惠來公園路徑（模擬）",
    scanId: "sim20260331hlp001",
    center: [24.155249, 120.639601],
    trees: 15,
    seed: 461,
  },
  {
    parkName: "臺中都會公園",
    pathId: "tc-metro-demo-20260401",
    pathName: "臺中都會公園主軸（模擬）",
    scanId: "sim20260401tcm001",
    center: [24.207703, 120.597378],
    trees: 19,
    seed: 471,
  },
  {
    parkName: "臺中中央公園",
    pathId: "tc-central-demo-20260402",
    pathName: "中央公園水域步道（模擬）",
    scanId: "sim20260402tcc001",
    center: [24.186977, 120.653178],
    trees: 24,
    seed: 481,
  },
  {
    parkName: "草悟道",
    pathId: "calligraphy-greenway-demo-20260403",
    pathName: "草悟道市民廣場段（模擬）",
    scanId: "sim20260403cgw001",
    center: [24.154081, 120.66365],
    trees: 14,
    seed: 491,
  },
  {
    parkName: "國立自然科學博物館",
    pathId: "nmns-demo-20260404",
    pathName: "科博館園區路徑（模擬）",
    scanId: "sim20260404nmns01",
    center: [24.157287, 120.666563],
    trees: 13,
    seed: 501,
  },
  {
    parkName: "廍子公園",
    pathId: "buzih-demo-20260405",
    pathName: "廍子公園步道（模擬）",
    scanId: "sim20260405bzp001",
    center: [24.167856, 120.73208],
    trees: 15,
    seed: 511,
  },
  {
    parkName: "黎新公園",
    pathId: "lixin-demo-20260406",
    pathName: "黎新公園路徑（模擬）",
    scanId: "sim20260406lxp001",
    center: [24.153222, 120.625862],
    trees: 12,
    seed: 521,
  },
  {
    parkName: "望高寮夜景公園",
    pathId: "wanggaoliao-demo-20260407",
    pathName: "望高寮夜景公園（模擬）",
    scanId: "sim20260407wgl001",
    center: [24.143768, 120.581947],
    trees: 11,
    seed: 531,
  },
];

function mulberry32(a) {
  return function () {
    let t = (a += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function estimateHeight(dbh, rand) {
  return Math.max(4.5, Math.min(28, 3.2 + 0.28 * dbh + (rand() - 0.5) * 2.5));
}

function makeTrees(n, seed) {
  const rand = mulberry32(seed);
  const trees = [];
  for (let i = 0; i < n; i++) {
    const id = `Tree_${String(i + 1).padStart(3, "0")}`;
    const bucket = rand();
    let dbh;
    if (bucket < 0.28) dbh = 12 + rand() * 18;
    else if (bucket < 0.72) dbh = 30 + rand() * 28;
    else dbh = 58 + rand() * 42;
    dbh = +dbh.toFixed(1);

    const growthRoll = rand();
    let prev;
    if (growthRoll < 0.12) prev = +(dbh + 0.1 + rand() * 0.4).toFixed(1);
    else if (growthRoll < 0.22) prev = dbh;
    else prev = +(dbh - (0.2 + rand() * 1.1)).toFixed(1);
    if (prev < 5) prev = +(5 + rand() * 3).toFixed(1);

    const method = rand() > 0.45 ? "circle" : "caliper";
    const along = -42 + (i / Math.max(1, n - 1)) * 78 + (rand() - 0.5) * 3.5;
    const side = (rand() > 0.5 ? 1 : -1) * (1.2 + rand() * 4.8);
    const z = +(1.25 + rand() * 0.25).toFixed(3);

    trees.push({
      Tree_ID: id,
      DBH_cm: dbh,
      previous_DBH_cm: prev,
      DBH_method: method,
      DBH_note: "模擬資料（臺中）",
      arc_coverage_deg: +(200 + rand() * 120).toFixed(1),
      dbh_is_strict_breast_height: rand() > 0.55,
      Height_m: +estimateHeight(dbh, rand).toFixed(1),
      GPS_Location: null,
      Local_XYZ_m: [+side.toFixed(3), +along.toFixed(3), z],
      Best_Photo: null,
      Mask_Path: null,
      Cross_Section_Image: null,
      "3D_Model_Path": null,
      Single_Tree_Ply: null,
      YOLO_confidence: +(0.38 + rand() * 0.45).toFixed(4),
      num_detections: 1,
      PointCloud_Preview: null,
    });
  }
  return trees;
}

const outDir = path.join(root, "src", "data", "inventories");
fs.mkdirSync(outDir, { recursive: true });

// 清掉舊的 sim*（含先前非台中）
for (const name of fs.readdirSync(outDir)) {
  if (name.startsWith("sim") && name.endsWith(".json")) {
    fs.unlinkSync(path.join(outDir, name));
    console.log("removed", name);
  }
}

// 路線座標請手改 src/data/scanBindings.ts（避開湖面），此腳本只重生 JSON。
for (const site of sites) {
  const trees = makeTrees(site.trees, site.seed);
  const y = site.scanId.slice(3, 7);
  const m = site.scanId.slice(7, 9);
  const d = site.scanId.slice(9, 11);
  const report = {
    created_at: `${y}-${m}-${d}T10:30:00`,
    scan_id: site.scanId,
    gps_available: false,
    num_trees: trees.length,
    trees,
  };
  fs.writeFileSync(
    path.join(outDir, `${site.scanId}.json`),
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8",
  );
  console.log("wrote", site.scanId, site.parkName, trees.length);
}

console.log(
  "inventories",
  sites.length,
  "(polylines stay in src/data/scanBindings.ts — do not auto-offset from park center)",
);
