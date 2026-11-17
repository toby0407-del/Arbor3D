import assert from "node:assert/strict";
import test from "node:test";
import { pathMapLayout } from "../src/lib/pathMapLayout.ts";
import routes from "../src/data/userScanRoutes.json";
import type { LatLng } from "../src/data/sites.ts";
import type { TreeRecord } from "../src/types.ts";

test("detail map uses the supplied park route instead of connecting arbitrary local coordinates",()=>{
  const route=routes[0].polyline as LatLng[];
  const trees=Array.from({length:18},(_,i)=>({Tree_ID:`Tree_${String(i).padStart(3,'0')}`,Local_XYZ_m:[1000*i,-3000*i,1.3],GPS_Location:null}) as TreeRecord);
  const layout=pathMapLayout(trees,route,'Tree_003')!;
  assert.equal(layout.line.length,route.length);
  assert.equal(layout.points.length,trees.length);
  assert.ok(layout.line[5].x>layout.line[0].x);
  assert.ok(layout.line.at(-1)!.y>layout.line[0].y);
  assert.ok(layout.points.find(p=>p.id==='Tree_003')!.label);
  assert.ok(layout.points.every(p=>p.x>=0&&p.x<=layout.width&&p.y>=0&&p.y<=layout.height));
  const labels=layout.points.filter(p=>p.label);
  for(let i=0;i<labels.length;i++)for(let j=i+1;j<labels.length;j++){
    const a=labels[i].label!,b=labels[j].label!;
    assert.ok(Math.abs(a.x-b.x)>=30 || Math.abs(a.y-b.y)>=16);
  }
});

test("fallback plots true local points with equal metric scales and no invented path",()=>{
  const trees=[{Tree_ID:'a',Local_XYZ_m:[0,0,0]},{Tree_ID:'b',Local_XYZ_m:[10,10,0]}] as TreeRecord[];
  const layout=pathMapLayout(trees)!;
  assert.equal(layout.line.length,0);
  assert.equal(layout.hasRoute,false);
  assert.ok(Math.abs((layout.points[1].x-layout.points[0].x)+(layout.points[1].y-layout.points[0].y))<1e-8);
});
