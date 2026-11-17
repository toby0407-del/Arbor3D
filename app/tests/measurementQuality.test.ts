import assert from "node:assert/strict";
import test from "node:test";
import { rankViews, qualityEvidence, qualityAccepted, qualityState } from "../src/lib/measurementQuality.ts";
import { trafficLight } from "../src/lib/status.ts";
import type { MeasurementQuality, ParkInventoryReport, TreeRecord } from "../src/types.ts";

const tree = {Tree_ID:"T1",DBH_cm:20,DBH_method:"circle",DBH_note:"ok",dbh_is_strict_breast_height:true} as TreeRecord;
const quality: MeasurementQuality = {schema_version:"arbor3d-quality-1",method:"circle",decision:"accepted",identifiable:true,
 probability:.99,target_probability:.95,tolerance_cm:1,model_id:"test-fixture",reasons:[],features:{}};

test("quality status cannot use confidence or fabricated acceptance flags to pass",()=>{
 assert.equal(qualityAccepted(null),false);
 assert.equal(qualityAccepted({...quality,probability:NaN}),false);
 assert.equal(qualityAccepted({...quality,model_id:null}),false);
 assert.equal(qualityAccepted({...quality,probability:.9}),false);
 assert.equal(qualityAccepted(quality),true);
 assert.match(qualityState(tree),/歷史結果/);
 assert.equal(trafficLight({...tree,measurement_quality:{...quality,decision:"review",reasons:["missing_calibration"]}}),"red");
});

test("rescan ranks only explicitly safe reachable candidates, including wrapped-angle rejection",()=>{
 const a={azimuth_deg:90,new_coverage_deg:30,time_s:10,safe:true,reachable:true};
 const ranked=rankViews([a,{...a,new_coverage_deg:300,safe:false},{...a,reachable:false},{...a,azimuth_deg:360},{...a,time_s:0},{...a,azimuth_deg:180,time_s:5}]);
 assert.deepEqual(ranked.map(v=>v.azimuth_deg),[180,90]);
});

test("evidence keeps missing features and tree identity blank, never uses YOLO confidence as precision",()=>{
 const report={scan_id:"s1",created_at:"2026-10-27",trees:[{...tree,YOLO_confidence:.99}]} as ParkInventoryReport;
 const row=qualityEvidence(report,{}).rows[0];
 assert.deepEqual(row.features,{});assert.equal(row.manual_dbh_cm,null);assert.equal(row.persistent_tree_id,"");
 assert.equal(row.strict_13m,false);assert.equal(row.split,"unassigned");
 assert.equal(qualityEvidence({...report,scan_id:"sim001"},{}).rows[0].source,"simulated");
});
