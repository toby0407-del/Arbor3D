import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const appRoot = path.resolve(import.meta.dirname, "..");
const inventoryRoot = path.join(appRoot, "src", "data", "inventories");

test("every simulated inventory uses labelled, varied and loadable synthetic media", () => {
  const files = fs.readdirSync(inventoryRoot).filter((name) => /^sim.*\.json$/i.test(name));
  assert.equal(files.length, 30);
  const masks = new Set<string>();
  const slices = new Set<string>();
  const clouds = new Set<string>();
  for (const file of files) {
    const report = JSON.parse(fs.readFileSync(path.join(inventoryRoot, file), "utf8"));
    assert.equal(report.dataset_kind, "simulated", file);
    assert.match(report.simulation_notice, /合成|模擬/, file);
    assert.match(report.simulation_media_source, /合成展示素材庫/, file);
    assert.ok(report.trees.length > 0, file);
    for (const tree of report.trees) {
      assert.match(tree.DBH_note, /模擬/, `${file}:${tree.Tree_ID}`);
      for (const field of [
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
      assert.equal(tree.Best_Photo, undefined, `${file}:${tree.Tree_ID}:Best_Photo`);
      assert.match(tree.Mask_Path, /synthetic-tree-evidence\/masks\/mask-\d{2}\.png$/);
      assert.match(tree.Cross_Section_Image, /synthetic-tree-evidence\/cross-sections\/cross-section-\d{2}\.png$/);
      assert.match(tree.PointCloud_Preview, /synthetic-tree-evidence\/point-clouds\/point-cloud-\d{2}\.png$/);
      masks.add(tree.Mask_Path);
      slices.add(tree.Cross_Section_Image);
      clouds.add(tree.PointCloud_Preview);
    }
  }
  assert.equal(masks.size, 4);
  assert.equal(slices.size, 4);
  assert.equal(clouds.size, 4);
});
