/** Code-drawn reference diagrams. Never use photographs or transformed images as point clouds. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const meta='<metadata>Arbor3D synthetic reference diagram; not field evidence; technical-v1</metadata>';
const svg=(body,w=1000,h=1040)=>`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}">${meta}${body}</svg>`;
const text=(x,y,value,size=24,extra='')=>`<text x="${x}" y="${y}" font-size="${size}" font-family="Arial, Microsoft JhengHei, sans-serif" ${extra}>${value}</text>`;

function section(tree){
  const dbh=Number(tree.DBH_cm), arc=Math.max(0,Math.min(360,Number(tree.arc_coverage_deg)||0));
  if(!(dbh>0))return svg('<rect width="1000" height="1040" fill="white"/>'+text(500,500,'截面資料不足',30,'text-anchor="middle"'));
  const r=dbh/200, span=r*2.2, cx=555,cy=525,scale=780/span,pr=r*scale;
  let body='<rect width="1000" height="1040" fill="white"/>';
  body+=text(500,36,'胸高切片俯視圖（由上往下看）',28,'text-anchor="middle"');
  body+=text(500,70,`DBH = ${dbh.toFixed(1)} 公分，涵蓋角度 = ${arc.toFixed(0)}°`,27,'text-anchor="middle"');
  body+=`<circle cx="${cx}" cy="${cy}" r="${pr}" fill="#c5e5b3" fill-opacity="0.78" stroke="#8fbd8c" stroke-width="3"/>`;
  for(let i=0;i<=6;i++){
    const p=145+i*130,q=135+i*130;
    body+=`<path d="M${p} 105V945 M135 ${q}H955" fill="none" stroke="#ccc" stroke-dasharray="2 3"/>`;
    body+=text(p,978,((p-cx)/scale).toFixed(2),21,'text-anchor="middle"');
    body+=text(120,q+7,((cy-q)/scale).toFixed(2),21,'text-anchor="end"');
  }
  body+='<rect x="135" y="105" width="820" height="840" fill="none" stroke="#222" stroke-width="2"/>';
  const count=Math.max(4,Math.round(arc/5));
  for(let i=0;i<count;i++){
    const a=(-arc/2+arc*i/(count-1))*Math.PI/180;
    body+=`<circle cx="${(cx+Math.cos(a)*pr).toFixed(2)}" cy="${(cy+Math.sin(a)*pr).toFixed(2)}" r="6.5" fill="#dc2626"/>`;
  }
  body+=`<path d="M${cx-15} ${cy}H${cx+15} M${cx} ${cy-15}V${cy+15}" stroke="#39883c" stroke-width="5"/>`;
  body+='<rect x="705" y="116" width="235" height="38" rx="3" fill="white" stroke="#ccc"/><circle cx="725" cy="135" r="6" fill="#dc2626"/>';
  body+=text(741,143,'胸高切片參考點',20)+text(545,1022,'X (m)',24,'text-anchor="middle"')+text(42,525,'Y (m)',24,'text-anchor="middle" transform="rotate(-90 42 525)"');
  return svg(body);
}

function cloud(identity,tree){
  let seed=2166136261;
  for(const c of identity){seed^=c.charCodeAt(0);seed=Math.imul(seed,16777619)>>>0;}
  const profile=seed%7;
  const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
  const groups=Array.from({length:12},()=>[]);
  const dot=(x,y)=>{if(x<35||x>965||y<40||y>1030)return;const shade=Math.floor(random()*12);groups[shade].push(`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(.8+random()*.9).toFixed(1)}"/>`);};
  const base=480+random()*70,lean=(random()-.5)*100;
  const width=Math.max(9,Math.min(35,Number(tree.DBH_cm)/2));
  const crownY=230+random()*120, crownW=profile===0?100+random()*50:180+random()*120;
  const crownH=profile===0?170:90+random()*95;
  const fork=profile===2||profile===5;
  const stem=(t)=>base+lean*t+Math.sin(t*5)*8;
  for(let i=0;i<1500;i++){const t=random();dot(stem(t)+(random()-.5)*width*(1-.55*t),960-t*(960-crownY),);}
  const branches=7+profile;
  for(let b=0;b<branches;b++){
    const t=.46+random()*.48,sy=960-t*(960-crownY),sx=stem(t);
    const side=b%2?-1:1,ex=base+side*crownW*(.3+random()*.7)+lean;
    const ey=crownY+(random()-.5)*crownH*1.5;
    for(let i=0;i<120;i++){const u=random();dot(sx+(ex-sx)*u+(random()-.5)*7,sy+(ey-sy)*u+(random()-.5)*7);}
    const rx=35+random()*crownW*.4,ry=35+random()*crownH*.55;
    for(let i=0;i<180;i++){const a=random()*Math.PI*2,r=Math.sqrt(random());dot(ex+Math.cos(a)*r*rx,ey+Math.sin(a)*r*ry);}
  }
  if(fork){for(let i=0;i<700;i++){const t=random();dot(stem(.35)+(t*130*(profile===2?1:-1))+(random()-.5)*width*.6,710-t*450);}}
  for(let i=0;i<500;i++){const a=random()*Math.PI*2,r=Math.sqrt(random());dot(base+lean+Math.cos(a)*r*crownW,crownY+Math.sin(a)*r*crownH);}
  for(let i=0;i<450;i++)dot(base-180+random()*360,960+(random()-.5)*12);
  const points=groups.map((pts,i)=>`<g fill="rgb(${85+i*7},${104+i*8},${76+i*6})">${pts.join('')}</g>`).join('');
  return svg('<rect width="1000" height="1100" fill="#10160f"/>'+`<g data-renderer="discrete-point-cloud" data-profile="${profile}">${points}</g>`,1000,1100);
}

export async function generateTechnicalPreviews(){
  let count=0;
  for(const file of await fs.readdir(path.join(root,'src/data/inventories'))){
    if(!/^sim.*\.json$/.test(file))continue;
    const report=JSON.parse(await fs.readFile(path.join(root,'src/data/inventories',file),'utf8'));
    if(report.dataset_kind!=='simulated')throw new Error('Only synthetic inventories may get reference diagrams');
    const dest=path.join(root,'public/scans',report.scan_id,'technical-v1');
    await fs.mkdir(dest,{recursive:true});
    const clouds=path.join(root,'public/scans',report.scan_id,'technical-v2');
    await fs.mkdir(clouds,{recursive:true});
    for(const tree of report.trees){
      if(!/^Tree_\d+$/.test(tree.Tree_ID))throw new Error('Unsafe tree ID');
      await fs.writeFile(path.join(dest,`${tree.Tree_ID}-section.svg`),section(tree));
      await fs.writeFile(path.join(clouds,`${tree.Tree_ID}-cloud.svg`),cloud(`${report.scan_id}:${tree.Tree_ID}`,tree));count++;
    }
  }
  console.log(`Generated ${count} upright reference sections and ${count} individual discrete point-cloud previews. Inventories unchanged.`);
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))await generateTechnicalPreviews();
