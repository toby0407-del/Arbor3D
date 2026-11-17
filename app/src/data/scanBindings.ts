import userRoutes from "./userScanRoutes.json";
import { hasReport } from "./inventory";

type LatLng = [number, number];

export type ScanBinding = {
  siteId?: string;
  routeReliability?: "osm-aligned" | "unverified" | "user-drawn";
  routeNote?: string;
  parkName: string;
  pathId: string;
  pathName: string;
  scanId: string;
  polyline: LatLng[];
};

/**
 * 實地盤點掃描與地點的綁定。
 * parkName 必須與 taiwan_sites.json 的 name 完全相同。
 */
export const SCAN_BINDINGS: ScanBinding[] = [
  ...(userRoutes as ScanBinding[]),
  {
    parkName: "逢甲大學",
    pathId: "fengchia-campus-20260818",
    pathName: "校園掃描路徑（8/18 · 7-11）",
    scanId: "20260818092855",
    // 沿 OSM pedestrian 405302435 的校內通道取點；位於學思樓／
    // 土木水利館之間，終點停在學思湖以南，不以兩端直線穿越地物。
    polyline: [
      [24.181228, 120.64674],
      [24.181239, 120.64682],
      [24.18125, 120.6469],
      [24.181261, 120.64698],
      [24.18127, 120.647047],
      [24.181288, 120.647095],
      [24.181306, 120.647144],
    ],
  },
];

export function bindingsForPark(parkName: string, siteId?: string): ScanBinding[] {
  return SCAN_BINDINGS.filter(
    (item) =>
      item.parkName === parkName &&
      (!siteId || !item.siteId || item.siteId === siteId),
  );
}

export function bindingHasInventory(item: ScanBinding): boolean {
  return Boolean(item.scanId) && hasReport(item.scanId);
}
