/** Camera framing only. No points are removed or moved. */
export function cloudFrame(positions: ArrayLike<number>, full = false) {
  const axes: number[][] = [[], [], []];
  const count = Math.floor(positions.length / 3);
  const step = full ? 1 : Math.max(1, Math.ceil(count / 40000));
  for (let i=0; i<count; i+=step) {
    const p = [positions[i*3],positions[i*3+1],positions[i*3+2]];
    if (p.every(Number.isFinite)) p.forEach((v,j)=>axes[j].push(v));
  }
  const limits = axes.map(a=>{
    a.sort((x,y)=>x-y);
    if (!a.length) return [-1,1];
    const trim = full || a.length < 100 ? 0 : Math.floor(a.length*.01);
    return [a[trim], a[a.length-1-trim]];
  });
  return {
    center: limits.map(([lo,hi])=>(lo+hi)/2),
    size: limits.map(([lo,hi])=>Math.max(.1,hi-lo)),
  };
}
