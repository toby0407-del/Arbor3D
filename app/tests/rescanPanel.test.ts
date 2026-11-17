import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { RescanPanel } from "../src/components/RescanPanel.tsx";
import type { ParkInventoryReport, TreeRecord } from "../src/types.ts";

test("rescan UI binds its overlay to the selected scan/tree and preserves unassessed counts", () => {
  const tree = {Tree_ID:"Tree_002", Rescan_Overlay_Image:"dbh/Tree_002_rescan.svg", Cross_Section_Image:"dbh/Tree_002.png",
    rescan_plan:{schema_version:"arbor3d-rescan-2",required:true,status:"pending_safety_check",reasons:[],coordinate_frame:"local_xy_ccw_from_positive_x",bin_deg:5,minimum_scope_deg:20,next_view_local_deg:0,precision_guaranteed:false,safety_status:"unverified",sectors:[{start_deg:350,end_deg:10,span_deg:20,view_local_deg:0}]}} as TreeRecord;
  const report = {scan_id:"scan-a",trees:[tree,{Tree_ID:"Tree_003"}]} as ParkInventoryReport;
  const html = renderToStaticMarkup(createElement(RescanPanel,{tree,report}));
  assert.ok(html.includes("/scans/scan-a/dbh/Tree_002_rescan.svg"));
  assert.ok(!html.includes("Tree_003_rescan"));
  assert.ok(html.includes("本批待處理 1 棵"));
  assert.ok(html.includes("1 棵尚未評估"));
  assert.ok(html.includes("350° → 10°"));
});

test("legacy evidence never receives an invented rescan overlay", () => {
  const tree = {Tree_ID:"Tree_001"} as TreeRecord;
  const report = {scan_id:"legacy",trees:[tree]} as ParkInventoryReport;
  const html = renderToStaticMarkup(createElement(RescanPanel,{tree,report}));
  assert.ok(html.includes("尚無這棵樹的截面缺口紀錄"));
  assert.ok(!html.includes("<img"));
});
