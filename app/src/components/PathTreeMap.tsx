import * as React from "react";
import { trafficLight } from "../lib/status";
import { pathMapLayout } from "../lib/pathMapLayout";
import type { LatLng } from "../data/sites";
import type { TrafficLight, TreeRecord } from "../types";

const FILL:Record<TrafficLight,string>={green:"#7dae7a",yellow:"#d2b56a",red:"#d08980"};
type Props={trees:TreeRecord[];selectedId:string|null;onPick?:(id:string)=>void;polyline?:LatLng[]};

export function PathTreeMap({trees,selectedId,onPick,polyline}:Props){
  const [zoomed,setZoomed]=React.useState(false);
  const layout=React.useMemo(()=>pathMapLayout(trees,polyline,selectedId),[trees,polyline,selectedId]);
  if(!layout)return <div className="path-db-empty">尚無路徑圖</div>;
  const byId=new Map(trees.map(t=>[t.Tree_ID,t]));
  const path=layout.line.map((p,i)=>`${i?'L':'M'}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ');
  const renderSvg=()=> <svg viewBox={`0 0 ${layout.width} ${layout.height}`} role="img" aria-label="路徑樹位">
    <path d={path} className="path-tree-map-line" fill="none" stroke="#ff8a00" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
    {layout.hasRoute && <g fill="#52674f" fontSize="12">
      <text x={layout.line[0].x-20} y={layout.line[0].y-10}>起</text>
      <text x={layout.line.at(-1)!.x-20} y={layout.line.at(-1)!.y+22}>終</text>
    </g>}
    {[...layout.points].sort((a,b)=>Number(a.id===selectedId)-Number(b.id===selectedId)).map(p=>{
      const tree=byId.get(p.id)!,on=p.id===selectedId;
      const short=p.id.replace(/^Tree_?/i,"");
      return <g key={p.id} className={`path-tree-map-node is-${trafficLight(tree)}${on?' is-on':''}`} role={onPick?'button':undefined} tabIndex={onPick?0:undefined} aria-label={p.id} aria-current={on?'true':undefined}
        onClick={()=>onPick?.(p.id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onPick?.(p.id);}}}>
        <title>{`${p.id}${layout.hasRoute?' · 沿線索引位置':' · 局部點雲座標'}`}</title>
        {on&&<circle cx={p.x} cy={p.y} r="12" className="path-tree-map-pulse"/>}
        {tree.rescan_plan?.required&&<circle cx={p.x} cy={p.y} r="10" fill="none" stroke="#b45309" strokeDasharray="3 2"/>}
        <circle cx={p.x} cy={p.y} r={on?7:5.5} className="path-tree-map-dot" fill={FILL[trafficLight(tree)]} stroke={on?'#ffd000':'#1a2216'} strokeWidth={on?3:1.5}/>
        {p.label&&<>
          <line x1={p.x} y1={p.y} x2={p.label.x} y2={p.label.y-4} stroke="#b0b8aa" strokeWidth=".7"/>
          <rect x={p.label.x-16} y={p.label.y-12} width="32" height="16" rx="3" fill="#fff" fillOpacity=".92"/>
          <text x={p.label.x} y={p.label.y} fontSize="11" fontWeight="800" fill="#1a2216" textAnchor="middle">{short}</text>
        </>}
      </g>;
    })}
    <g transform="translate(18,274)" stroke="#657c64" fill="#52674f" fontSize="11">
      <path d={`M0,-4 V0 H${layout.scaleMeters*layout.scale} V-4`} fill="none" strokeWidth="1.5"/>
      <text x="0" y="16" stroke="none">{layout.scaleMeters} m</text>
    </g>
    <text x={layout.width-12} y="289" textAnchor="end" fontSize="10" fill="#65705e">{layout.hasRoute?'沿線索引位置':'局部點雲座標'}</text>
  </svg>;
  return <>
    <div className="path-tree-map"><button type="button" className="path-tree-map-zoom" aria-label="放大路徑圖" onClick={()=>setZoomed(true)}>＋</button><div className="path-tree-map-main">{renderSvg()}</div></div>
    {zoomed&&<div className="path-lightbox" role="dialog" aria-modal="true" aria-label="放大路徑圖" onClick={()=>setZoomed(false)}>
      <div className="path-lightbox-card" onClick={e=>e.stopPropagation()}><header><strong>路徑圖</strong><button type="button" className="ghost-btn" onClick={()=>setZoomed(false)}>關閉</button></header>
        <div className="path-tree-map path-tree-map--zoom"><div className="path-tree-map-main">{renderSvg()}</div></div>
      </div>
    </div>}
  </>;
}
