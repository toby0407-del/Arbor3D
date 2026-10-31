import type { LatLng } from "../data/sites";
import type { TreeRecord } from "../types";
import { treesAlongPolyline } from "./treePlacement";
import { haversineMeters } from "./gpx";

export function pathMapLayout(trees: TreeRecord[], route: LatLng[] = [], selectedId: string | null = null) {
  if (!trees.length) return null;
  const width=420, height=300, pad=42;
  const hasRoute=route.length>=2;
  const origin=route[0] ?? [0,0];
  const toMeters=(p:LatLng)=>({x:(p[1]-origin[1])*111320*Math.cos(origin[0]*Math.PI/180),y:(p[0]-origin[0])*111320});
  const markers=hasRoute ? treesAlongPolyline(route,trees).map(m=>({id:m.id,...toMeters(m.latlng)}))
    : trees.map(t=>({id:t.Tree_ID,x:t.Local_XYZ_m[0],y:t.Local_XYZ_m[1]}));
  const routeMeters=hasRoute ? route.map(toMeters) : [];
  const all=[...markers,...routeMeters];
  const minX=Math.min(...all.map(p=>p.x)), maxX=Math.max(...all.map(p=>p.x));
  const minY=Math.min(...all.map(p=>p.y)), maxY=Math.max(...all.map(p=>p.y));
  const spanX=Math.max(1,maxX-minX), spanY=Math.max(1,maxY-minY);
  const scale=Math.min((width-2*pad)/spanX,(height-2*pad)/spanY);
  const project=(p:{x:number;y:number})=>({x:width/2+(p.x-(minX+maxX)/2)*scale,y:height/2-(p.y-(minY+maxY)/2)*scale});
  const points=markers.map(m=>({id:m.id,...project(m)}));
  const boxes:{x:number;y:number;w:number;h:number}[]=[];
  const labels=new Map<string,{x:number;y:number}>();
  const ordered=[...points].sort((a,b)=>Number(b.id===selectedId)-Number(a.id===selectedId));
  for(const p of ordered){
    const w=Math.max(32,p.id.replace(/^Tree_?/i,"").length*7+8),h=16;
    for(const [dx,dy] of [[0,-18],[0,24],[30,-12],[-30,-12],[36,20],[-36,20],[0,-36],[0,42]]){
      const x=p.x+dx,y=p.y+dy,box={x:x-w/2,y:y-h+3,w,h};
      if(box.x<8||box.x+w>width-8||box.y<8||box.y+h>height-28)continue;
      if(boxes.some(b=>box.x<b.x+b.w+3&&box.x+box.w+3>b.x&&box.y<b.y+b.h+3&&box.y+box.h+3>b.y))continue;
      if(points.some(n=>n.id!==p.id&&n.x>box.x-6&&n.x<box.x+w+6&&n.y>box.y-6&&n.y<box.y+h+6))continue;
      boxes.push(box);labels.set(p.id,{x,y});break;
    }
  }
  const target=70/scale,base=10**Math.floor(Math.log10(target));
  const scaleMeters=([5,2,1].find(n=>n*base<=target)??1)*base;
  const distanceM=route.slice(1).reduce((sum,p,i)=>sum+haversineMeters(route[i][0],route[i][1],p[0],p[1]),0);
  return {width,height,hasRoute,scale,scaleMeters,distanceM,line:routeMeters.map(project),points:points.map(p=>({...p,label:labels.get(p.id)}))};
}
