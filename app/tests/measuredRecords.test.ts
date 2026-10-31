import assert from "node:assert/strict";
import test from "node:test";
import { partitionMeasuredRecords } from "../scripts/measured-records.mjs";

test("published count follows supported measurements without padding or a fixed tree limit",()=>{
  const records=Array.from({length:61},(_,i)=>({Tree_ID:`T${i}`,DBH_cm:i%2 ? 20+i : null}));
  const before=JSON.stringify(records);
  const {measured,excluded}=partitionMeasuredRecords(records);
  assert.equal(measured.length,30);
  assert.equal(excluded.length,31);
  assert.equal(JSON.stringify(records),before);
  const all=partitionMeasuredRecords(Array.from({length:75},(_,i)=>({DBH_cm:i+1})));
  assert.equal(all.measured.length,75);
  assert.deepEqual(partitionMeasuredRecords([{DBH_cm:0},{DBH_cm:-1},{DBH_cm:NaN},{DBH_cm:Infinity}]).measured,[]);
});
