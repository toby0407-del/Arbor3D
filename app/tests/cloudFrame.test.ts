import assert from "node:assert/strict";
import test from "node:test";
import { cloudFrame } from "../src/lib/cloudFrame.ts";
import { classifyGrowth, quarterlyGrowth } from "../src/lib/growth.ts";
import type { QuarterlyObservation } from "../src/types.ts";

test("focused framing resists remote points while full view and source coordinates retain them",()=>{
  const p:number[]=[];
  for(let i=0;i<1000;i++)p.push(Math.sin(i),Math.cos(i),i/100);
  p.push(1000,1000,1000);
  const before=[...p];
  const focus=cloudFrame(p),full=cloudFrame(p,true);
  assert.ok(focus.size[2]<11);
  assert.ok(full.size[2]>=1000);
  assert.deepEqual(p,before);
});

test("relaxed growth alerts retain missing-measurement warnings and significant decline",()=>{
  assert.equal(classifyGrowth({dbhCm:120}),"watch");
  assert.equal(classifyGrowth({dbhCm:50,note:"gap"}),"watch");
  assert.equal(classifyGrowth({dbhCm:null}),"abnormal");
  const rows=(value:number)=>[
    {date:"2026-03-01",quarter:"2026Q1",simulated_ai_dbh_cm:40,simulated_height_m:8},
    {date:"2026-06-01",quarter:"2026Q2",simulated_ai_dbh_cm:value,simulated_height_m:8},
  ] as QuarterlyObservation[];
  assert.equal(quarterlyGrowth(rows(39.3)).warning,false);
  assert.equal(quarterlyGrowth(rows(38.8)).warning,true);
});
