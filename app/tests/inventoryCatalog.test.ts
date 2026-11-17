import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const REAL_SCAN_IDS = ["20260818092855", "20261020165350"];

function namesAt(path: string, predicate: (name: string) => boolean): string[] {
  return readdirSync(path)
    .filter(predicate)
    .sort();
}

test("盤點目錄只包含逢甲與惠來公園的實地資料", () => {
  const inventoryDir = resolve("src/data/inventories");
  const inventoryFiles = namesAt(inventoryDir, (name) => name.endsWith(".json"));

  assert.deepEqual(
    inventoryFiles,
    REAL_SCAN_IDS.map((scanId) => `${scanId}.json`),
  );

  for (const file of inventoryFiles) {
    const report = JSON.parse(readFileSync(resolve(inventoryDir, file), "utf8"));
    assert.equal(report.scan_id, file.replace(/\.json$/, ""));
    assert.notEqual(report.dataset_kind, "simulated");
  }

  const scanDirs = namesAt(
    resolve("public/scans"),
    (name) => !name.startsWith("_") && name !== ".gitkeep",
  );
  assert.deepEqual(scanDirs, REAL_SCAN_IDS);

  const analysisFiles = namesAt(
    resolve("public/analysis"),
    (name) => name.endsWith(".json"),
  );
  assert.deepEqual(analysisFiles, ["20260818092855.json"]);
  assert.equal(existsSync(resolve("public/scans/_shared/synthetic-tree-evidence")), false);
});

test("地圖綁定只包含兩個實地盤點", () => {
  const userRoutes = JSON.parse(readFileSync(resolve("src/data/userScanRoutes.json"), "utf8"));
  assert.deepEqual(
    userRoutes.map((route: { scanId: string }) => route.scanId),
    ["20261020165350"],
  );

  const bindingsSource = readFileSync(resolve("src/data/scanBindings.ts"), "utf8");
  assert.match(bindingsSource, /20260818092855/);
  assert.doesNotMatch(bindingsSource, /sim\d/i);

  const simulationSites = JSON.parse(
    readFileSync(resolve("scripts/park-simulation-sites.json"), "utf8"),
  );
  assert.deepEqual(simulationSites, []);
});
