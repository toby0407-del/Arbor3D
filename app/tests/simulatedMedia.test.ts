import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const appRoot = path.resolve(import.meta.dirname, "..");
const inventoryRoot = path.join(appRoot, "src", "data", "inventories");

test("every simulated inventory is labelled and has loadable demo media", () => {
  const files = fs.readdirSync(inventoryRoot).filter((name) => /^sim.*\.json$/i.test(name));
  assert.equal(files.length, 24);
  for (const file of files) {
    const report = JSON.parse(fs.readFileSync(path.join(inventoryRoot, file), "utf8"));
    assert.equal(report.dataset_kind, "simulated", file);
    assert.match(report.simulation_notice, /合成|模擬/, file);
    assert.ok(report.trees.length > 0, file);
    for (const tree of report.trees) {
      assert.match(tree.DBH_note, /模擬/, `${file}:${tree.Tree_ID}`);
      for (const field of [
        "Best_Photo",
        "Mask_Path",
        "Cross_Section_Image",
        "PointCloud_Preview",
        "3D_Model_Path",
        "Single_Tree_Ply",
      ]) {
        assert.ok(tree[field], `${file}:${tree.Tree_ID}:${field}`);
        assert.ok(
          fs.existsSync(path.join(appRoot, "public", "scans", report.scan_id, tree[field])),
          `${file}:${tree.Tree_ID}:${field}`,
        );
      }
    }
  }
});
