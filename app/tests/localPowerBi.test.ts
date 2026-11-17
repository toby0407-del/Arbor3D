import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile, readdir } from 'node:fs/promises';
import { currentAnalyticsFingerprint, parseLocalPowerBi } from '../src/lib/localPowerBi.ts';
import { totalCo2Ton } from '../src/lib/carbon.ts';
import type { ParkInventoryReport } from '../src/types.ts';
const report={scan_id:'s',created_at:'2026-10-28',trees:[{Tree_ID:'T',DBH_cm:20}]} as ParkInventoryReport;
const snapshot={schema_version:1,scan_id:'s',dataset_kind:'observed',input_fingerprint:'a'.repeat(64),
  engine:'Power BI Desktop / Analysis Services',calculated_at:'2026-10-28T00:00:00Z',published_at:'2026-10-28T00:00:01Z',
  metrics:{observations:1,paired_count:0,review_count:1,mae_cm:null,rmse_cm:null,bias_cm:null,mape_pct:null,average_dbh_cm:20,co2_ton:null,demo_pairs:null,demo_mae_cm:null}};
test('Desktop snapshots reject other scans, synthetic evidence and invented accuracy',()=>{
  assert.equal(parseLocalPowerBi(snapshot,report).metrics.mae_cm,null);
  assert.throws(()=>parseLocalPowerBi({...snapshot,scan_id:'other'},report));
  assert.throws(()=>parseLocalPowerBi({...snapshot,dataset_kind:'simulated'},report));
  assert.throws(()=>parseLocalPowerBi({...snapshot,metrics:{...snapshot.metrics,mae_cm:0}},report));
  assert.throws(()=>parseLocalPowerBi({...snapshot,metrics:{...snapshot.metrics,co2_ton:Infinity}},report));
});
test('Desktop freshness changes when a measurement or original observation changes',async()=>{
  const original=await currentAnalyticsFingerprint(report,{});
  assert.equal(original,await currentAnalyticsFingerprint(report,{}));
  assert.equal(original,await currentAnalyticsFingerprint({trees:report.trees,created_at:report.created_at,scan_id:report.scan_id} as ParkInventoryReport,{}));
  const field={dbhCm:'22',heightM:'',coeff:'',note:'',measuredAt:'2026-10-28',strict13m:true};
  assert.notEqual(original,await currentAnalyticsFingerprint(report,{T:field}));
  assert.notEqual(original,await currentAnalyticsFingerprint({...report,trees:[{...report.trees[0],DBH_cm:21}]},{}));
});
test('every published Desktop snapshot has a matching App scan and keeps synthetic accuracy separate',async()=>{
  const folder=new URL('../public/analysis/',import.meta.url);
  for(const file of await readdir(folder)) {
    if(!file.endsWith('.json'))continue;
    const value=JSON.parse(await readFile(new URL(file,folder),'utf8'));
    const input=JSON.parse(await readFile(new URL(`../public/scans/${value.scan_id}/inventory.json`,import.meta.url),'utf8'));
    parseLocalPowerBi(value,input);
    if(value.dataset_kind==='simulated') {
      assert.equal(value.metrics.mae_cm,null);
      assert.ok(Math.abs(totalCo2Ton(input.trees,{},input.created_at)-value.metrics.co2_ton)<1e-8, 'App and Desktop use the same stored reference and formula');
    }
  }
});
