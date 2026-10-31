import assert from "node:assert/strict";
import test from "node:test";
import { trafficLight } from "../src/lib/status.ts";
import type { TreeRecord } from "../src/types.ts";

test("explicitly pending preview evidence is yellow, never promoted to accepted measurements",()=>{
  const pending = {Tree_ID:"T1",measurement_state:"pending_evidence",DBH_cm:null,DBH_note:"no_measurement",DBH_method:"unresolved",dbh_is_strict_breast_height:false} as TreeRecord;
  assert.equal(trafficLight(pending),"yellow");
  assert.equal(trafficLight({...pending,DBH_cm:20}),"yellow");
  assert.equal(trafficLight({...pending,measurement_state:undefined}),"red");
  assert.equal(trafficLight({...pending,DBH_cm:-1}),"red");
  assert.equal(trafficLight({...pending,measurement_quality:{decision:"review"} as TreeRecord["measurement_quality"]}),"red");
});
