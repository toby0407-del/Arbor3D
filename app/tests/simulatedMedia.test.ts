import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { technicalPreviewUrl } from '../src/lib/scanMedia.ts';
import type { ParkInventoryReport } from '../src/types.ts';

const appRoot = path.resolve(import.meta.dirname, "..");
const inventoryRoot = path.join(appRoot, "src", "data", "inventories");

test('all displayed technical previews use upright plots and discrete points, preserving observed media',()=>{
  const uniqueClouds=new Set<string>();
  for(const file of fs.readdirSync(inventoryRoot).filter(n=>n.endsWith('.json'))){
    const report=JSON.parse(fs.readFileSync(path.join(inventoryRoot,file),'utf8')) as ParkInventoryReport;
    for(const tree of report.trees){
      const section=technicalPreviewUrl(report,tree,'section')!;
      const cloud=technicalPreviewUrl(report,tree,'cloud')!;
      if(report.dataset_kind!=='simulated'){
        assert.equal(section,`/scans/${report.scan_id}/${tree.Cross_Section_Image}`);
        assert.equal(cloud,`/scans/${report.scan_id}/${tree.PointCloud_Preview}`);
        continue;
      }
      assert.ok(!section.includes('synthetic-tree-evidence'));
      assert.ok(!cloud.includes('synthetic-tree-evidence'));
      const read=(url:string)=>fs.readFileSync(path.join(appRoot,'public',url),'utf8');
      const slice=read(section),points=read(cloud);
      assert.match(slice,/胸高切片俯視圖/);
      assert.match(slice,/fill="#dc2626"/);
      if(tree.DBH_cm!=null)assert.ok(slice.includes(`DBH = ${tree.DBH_cm.toFixed(1)} 公分`));
      assert.ok(!slice.includes('<image')&&!slice.includes('<filter'));
      assert.ok(!slice.includes('<g transform='));
      assert.ok(!uniqueClouds.has(points), `Repeated cloud for ${report.scan_id}:${tree.Tree_ID}`);
      uniqueClouds.add(points);
      assert.match(points,/data-renderer="discrete-point-cloud"/);
      assert.ok((points.match(/<circle /g)||[]).length>3000);
      assert.ok(!points.includes('<image')&&!points.includes('<filter')&&!points.includes('<path'));
    }
  }
  assert.equal(uniqueClouds.size,450);
});

test("every currently published tree has a loadable cross-section image", () => {
  const files = fs.readdirSync(inventoryRoot).filter((name) => name.endsWith(".json"));
  let treeCount = 0;
  for (const file of files) {
    const report = JSON.parse(fs.readFileSync(path.join(inventoryRoot, file), "utf8"));
    for (const tree of report.trees ?? []) {
      treeCount += 1;
      assert.ok(tree.Cross_Section_Image, `${file}:${tree.Tree_ID}:Cross_Section_Image`);
      assert.ok(
        fs.existsSync(path.resolve(appRoot, "public", "scans", report.scan_id, tree.Cross_Section_Image)),
        `${file}:${tree.Tree_ID}:Cross_Section_Image file`,
      );
    }
  }
  assert.equal(treeCount, 466);
});

test("every simulated inventory uses labelled, varied and loadable synthetic media", () => {
  const files = fs.readdirSync(inventoryRoot).filter((name) => /^sim.*\.json$/i.test(name));
  assert.equal(files.length, 29);
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
  assert.equal(masks.size, 12);
  assert.equal(slices.size, 12);
  assert.equal(clouds.size, 12);
});

test("every enabled synthetic route has a published inventory and all three evidence images", () => {
  const bindingSource = fs.readFileSync(path.join(appRoot, "src/data/scanBindings.ts"), "utf8");
  const bound = [...bindingSource.matchAll(/scanId:\s*"(sim[^"]+)"/g)].map((match) => match[1]);
  const extra = JSON.parse(fs.readFileSync(path.join(appRoot, "src/data/extraParkBindings.json"), "utf8"));
  const scanIds = [...bound, ...extra.map((item: { scanId: string }) => item.scanId)];
  assert.equal(scanIds.length, 17);
  assert.equal(new Set(scanIds).size, 17);
  for (const scanId of scanIds) {
    const reportPath = path.join(inventoryRoot, `${scanId}.json`);
    assert.ok(fs.existsSync(reportPath), scanId);
    const report = JSON.parse(fs.readFileSync(reportPath, "utf8"));
    assert.ok(report.trees.length > 0, scanId);
    for (const tree of report.trees) {
      assert.ok(tree.Mask_Path, `${scanId}:${tree.Tree_ID}:Mask_Path`);
      assert.ok(tree.Cross_Section_Image, `${scanId}:${tree.Tree_ID}:Cross_Section_Image`);
      assert.ok(tree.PointCloud_Preview, `${scanId}:${tree.Tree_ID}:PointCloud_Preview`);
    }
  }
});
