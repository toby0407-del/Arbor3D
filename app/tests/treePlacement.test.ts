import assert from "node:assert/strict";
import test from "node:test";
import { treesAlongPolyline } from "../src/lib/treePlacement.ts";
import type { TreeRecord } from "../src/types.ts";
import type { LatLng } from "../src/data/sites.ts";

test("unlocated trees follow the route curve without using unregistered local offsets",()=>{
  const route:LatLng[]=[[24,120],[24,120.001],[23.999,120.001]];
  const trees=[0,1,2].map(i=>({Tree_ID:`T${i}`,Local_XYZ_m:[5000,-5000,1.3],GPS_Location:null,DBH_cm:30,DBH_note:"ok",dbh_is_strict_breast_height:true}) as TreeRecord);
  const before=JSON.stringify(trees);
  const markers=treesAlongPolyline(route,trees);
  assert.deepEqual(markers[0].latlng,route[0]);
  assert.deepEqual(markers[2].latlng,route[2]);
  assert.ok(markers[1].latlng[0]>=23.99892 && markers[1].latlng[0]<=24.00008);
  assert.ok(markers[1].latlng[1]>=119.99992 && markers[1].latlng[1]<=120.00108);
  assert.equal(markers.length,trees.length);
  assert.deepEqual(treesAlongPolyline(route,trees),markers);
  assert.ok(markers.every(t=>t.placement==='route-reference'));
  assert.equal(JSON.stringify(trees),before);
  trees[1].GPS_Location=[24.2,120.5];
  const mixed=treesAlongPolyline(route,trees);
  assert.deepEqual(mixed[1].latlng,[24.2,120.5]);
  assert.equal(mixed[1].placement,'gps');
});
