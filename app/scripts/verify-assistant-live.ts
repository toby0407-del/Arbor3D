// Explicit local integration evaluation; real model replies are saved privately.
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { inventoryAssistantContext } from '../src/lib/assistant.js';
import type { ParkInventoryReport } from '../src/types.js';
const label=process.argv[2] || 'verification';
if(!/^[a-z0-9-]+$/.test(label)) throw new Error('Use a safe evidence label');
const output=path.resolve(`../.runtime/assistant-${label}.json`);
const observed=JSON.parse(await fs.readFile('public/scans/20260818092855/inventory.json','utf8')) as ParkInventoryReport;
const manifest=JSON.parse(await fs.readFile('scenarios/parks/manifest.json','utf8'));
const scenario=JSON.parse(await fs.readFile(`public/scans/${manifest.sites[0].scanId}/inventory.json`,'utf8')) as ParkInventoryReport;
const cases=[
  {report:observed,question:'這批有幾棵樹？需複核、待確認各幾棵？總共幾棵需要人工核對？'},
  {report:observed,question:'哪一棵樹的胸徑最大？請列出樹號與胸徑。'},
  {report:observed,question:'這批資料的 MAE 和準確率是多少？沒有配對的話請直接說明。'},
  {report:observed,question:'目前沒有開通 Fabric，我可以怎麼用本機 Power BI 更新 App？'},
  {report:observed,question:'Tree_999 的胸徑是多少？資料沒有這棵就不要猜。'},
  {report:scenario,question:'這個公園有幾棵樹？需要複核的樹號是哪些？'},
  {report:scenario,question:'哪些樹要優先現場複核？'},
];
const results=[];
for(const item of cases){
  const context=inventoryAssistantContext(item.report===observed?'逢甲大學':manifest.sites[0].parkName,'盤點路線',item.report,{});
  const started=Date.now();
  try{
    const response=await fetch('http://127.0.0.1:5324/api/assistant',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({question:item.question,context}),signal:AbortSignal.timeout(75000)});
    const reply=await response.json();
    results.push({question:item.question,scan_id:item.report.scan_id,expected:context.summary,status:response.status,elapsed_ms:Date.now()-started,...reply});
  }catch(error){results.push({question:item.question,status:0,elapsed_ms:Date.now()-started,error:String(error)});}
  await fs.mkdir(path.dirname(output),{recursive:true});
  await fs.writeFile(output,JSON.stringify({tested_at:new Date().toISOString(),results},null,2));
  console.log(JSON.stringify(results.at(-1)));
}
