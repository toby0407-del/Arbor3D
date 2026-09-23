import type { ParkInventoryReport } from "../types";

/**
 * 遠端觀測檔規則：
 * 1. 把 park_inventory_report.json 複製成
 *    src/data/inventories/{scan_id}.json
 * 2. 在 scanBindings.ts 綁到公園與路徑
 * 3. 照片／剖面／ply 放到 public/scans/{scan_id}/ 對應 JSON 裡的相對路徑
 */
const modules = import.meta.glob("./inventories/*.json", {
  import: "default",
}) as Record<string, () => Promise<ParkInventoryReport>>;

const byScanId = new Map<string, ParkInventoryReport>();
const loadersByScanId = new Map<string, () => Promise<ParkInventoryReport>>();
const pending = new Map<string, Promise<ParkInventoryReport | undefined>>();

for (const [path, loader] of Object.entries(modules)) {
  const fromName = path.split("/").pop()?.replace(/\.json$/i, "") ?? "";
  if (fromName) loadersByScanId.set(fromName, loader);
}

export function getReport(scanId: string | null | undefined): ParkInventoryReport | undefined {
  if (!scanId) return undefined;
  return byScanId.get(scanId);
}

export function hasReport(scanId: string | null | undefined): boolean {
  return Boolean(scanId && (byScanId.has(scanId) || loadersByScanId.has(scanId)));
}

export function listLoadedScanIds(): string[] {
  return [...byScanId.keys()].sort();
}

export function listAvailableScanIds(): string[] {
  return [...new Set([...loadersByScanId.keys(), ...byScanId.keys()])].sort();
}

export async function loadReport(
  scanId: string | null | undefined,
): Promise<ParkInventoryReport | undefined> {
  if (!scanId) return undefined;
  const loaded = byScanId.get(scanId);
  if (loaded) return loaded;
  const inFlight = pending.get(scanId);
  if (inFlight) return inFlight;
  const loader = loadersByScanId.get(scanId);
  if (!loader) return undefined;
  const request = loader()
    .then((report) => {
      const resolvedId = report.scan_id || scanId;
      byScanId.set(resolvedId, report);
      if (resolvedId !== scanId) byScanId.set(scanId, report);
      return report;
    })
    .finally(() => pending.delete(scanId));
  pending.set(scanId, request);
  return request;
}
