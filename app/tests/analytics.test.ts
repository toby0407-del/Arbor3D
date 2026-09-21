import assert from 'node:assert/strict';
import test from 'node:test';
import { temporalGrowth } from '../src/lib/growth.ts';
import { analyticsInput, positive } from '../src/lib/analytics.ts';
import { inventoryToCsv } from '../src/lib/csv.ts';
import type { ParkInventoryReport } from '../src/types.ts';
const options = {dbhCm:20, heightM:null, heightEstimated:true, scanIso:'2026-07-20T10:00:00'};
test('nearby survey date remains simulated, exact observation is AI by default', () => {
  const t=temporalGrowth(options);
  assert.equal(t.current.source,'ai');
  assert.equal(t.previous.source,'sim');
  assert.equal(t.trend.source,'sim');
  assert.equal(t.points.filter(p=>p.source!=='sim').length,1);
});
test('manual source is explicit and never spreads to other months',()=>{
  const t=temporalGrowth({...options,baseSource:'measured'});
  assert.equal(t.current.source,'measured');
  assert.equal(t.points.filter(p=>p.source==='measured').length,1);
});
test('export preserves missing manual values and unconfirmed height',()=>{
  const r={scan_id:'s',created_at:'2026-01-01',trees:[{Tree_ID:'T',DBH_cm:20}]} as ParkInventoryReport;
  assert.deepEqual(analyticsInput(r,{}).manual_measurements,[]);
  const m=analyticsInput(r,{T:{dbhCm:'21',heightM:'',note:'',coeff:'',measuredAt:'2026-01-01'}}).manual_measurements[0];
  assert.equal(m.strict_13m,false); assert.equal(m.manual_dbh_cm,21);
});
test('measurement parser rejects nonpositive and nonfinite',()=>{
  for(const v of [null,'',0,-1,Infinity,'NaN',true]) assert.equal(positive(v),null);
});
test('legacy CSV shields spreadsheet formulas and labels derived values',()=>{
  const r={Tree_ID:'=1+1',DBH_cm:20,DBH_method:'circle',DBH_note:'ok',dbh_is_strict_breast_height:true} as ParkInventoryReport['trees'][number];
  const text=inventoryToCsv([r],{},'2026-01-01');
  assert.ok(text.includes("'=1+1")); assert.ok(text.includes('公式推估'));
});

test('empty notes cannot turn nonstandard measurements green', async()=>{
  const {trafficLight, inventoryStats}=await import('../src/lib/status.ts');
  const base={Tree_ID:'T',DBH_cm:20,DBH_method:'circle',DBH_note:'',dbh_is_strict_breast_height:false} as ParkInventoryReport['trees'][number];
  assert.equal(trafficLight(base),'yellow');
  assert.equal(trafficLight({...base,DBH_cm:50,DBH_method:'caliper'}),'red');
  assert.equal(inventoryStats([base]).review,1);
  assert.equal(trafficLight({...base,dbh_is_strict_breast_height:true}),'green');
});
