import type { LatLng } from "../data/sites";
import { haversineMeters } from "./gpx";
import { trafficLight } from "./status";
import { compareTreeIds } from "./treeOrder";
import type { TrafficLight, TreeRecord } from "../types";

export type MapTreeMarker = {
  id: string;
  latlng: LatLng;
  light: TrafficLight;
  placement: "gps" | "route-reference";
};

function interpolate(
  polyline: LatLng[],
  cum: number[],
  total: number,
  t: number,
): LatLng {
  const dist = Math.min(1, Math.max(0, t)) * total;
  for (let i = 1; i < polyline.length; i += 1) {
    if (cum[i] >= dist || i === polyline.length - 1) {
      const span = cum[i] - cum[i - 1] || 1;
      const u = (dist - cum[i - 1]) / span;
      const a = polyline[i - 1];
      const b = polyline[i];
      return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u];
    }
  }
  return polyline[polyline.length - 1];
}

function layoutFraction(id: string, salt: string) {
  let hash = 2166136261;
  for (const char of `${salt}:${id}`) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  hash ^= hash >>> 16;
  hash = Math.imul(hash, 0x7feb352d);
  hash ^= hash >>> 15;
  hash = Math.imul(hash, 0x846ca68b);
  hash ^= hash >>> 16;
  return (hash >>> 0) / 4294967295;
}

/** Stable, irregular route-index layout only; source measurements are unchanged. */
export function treesAlongPolyline(
  polyline: LatLng[],
  trees: TreeRecord[],
): MapTreeMarker[] {
  if (polyline.length < 2 || trees.length === 0) return [];
  trees = [...trees].sort(compareTreeIds);

  const withGps = trees.filter(
    (tree) =>
      tree.GPS_Location != null &&
      Number.isFinite(tree.GPS_Location[0]) &&
      Number.isFinite(tree.GPS_Location[1]) && Math.abs(tree.GPS_Location[0]) <= 90 && Math.abs(tree.GPS_Location[1]) <= 180,
  );
  if (withGps.length === trees.length) {
    return withGps.map((tree) => ({
      id: tree.Tree_ID,
      latlng: tree.GPS_Location as LatLng,
      light: trafficLight(tree),
      placement: "gps",
    }));
  }

  const cum = [0];
  for (let i = 1; i < polyline.length; i += 1) {
    cum.push(
      cum[i - 1] +
        haversineMeters(
          polyline[i - 1][0],
          polyline[i - 1][1],
          polyline[i][0],
          polyline[i][1],
        ),
    );
  }
  const total = cum[cum.length - 1];
  if (total <= 0) {
    return trees.map((tree) => ({
      id: tree.Tree_ID,
      latlng: polyline[0],
      light: trafficLight(tree),
      placement: "route-reference",
    }));
  }

  const gaps = trees.slice(1).map(tree => .4 + layoutFraction(tree.Tree_ID, "spacing") * 1.6);
  const length = gaps.reduce((sum,gap)=>sum+gap,0) || 1;
  let progress = 0;
  return trees.map((tree, index) => {
    const gps = tree.GPS_Location;
    const validGps = gps != null && Number.isFinite(gps[0]) && Number.isFinite(gps[1]) && Math.abs(gps[0]) <= 90 && Math.abs(gps[1]) <= 180;
    if (index > 0) progress += gaps[index-1];
    const t = trees.length === 1 ? .5 : progress / length;
    const onPath = interpolate(polyline, cum, total, t);
    const before = interpolate(polyline, cum, total, Math.max(0,t-.002));
    const after = interpolate(polyline, cum, total, Math.min(1,t+.002));
    const latitudeScale = Math.cos(onPath[0]*Math.PI/180);
    const north = (after[0]-before[0])*111320;
    const east = (after[1]-before[1])*111320*latitudeScale;
    const norm = Math.hypot(north,east) || 1;
    const offset = index === 0 || index === trees.length-1 ? 0 : (layoutFraction(tree.Tree_ID,"side")-.5)*14;
    const placed: LatLng = [onPath[0]+east/norm*offset/111320,onPath[1]-north/norm*offset/(111320*latitudeScale)];
    return {
      id: tree.Tree_ID,
      latlng: validGps ? gps : placed,
      light: trafficLight(tree),
      placement: validGps ? "gps" as const : "route-reference" as const,
    };
  });
}
