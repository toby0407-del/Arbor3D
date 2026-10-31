/** 掃描附件放在 public/scans/{scanId}/ 底下，路徑與 JSON 欄位相同。 */
import type { ParkInventoryReport, TreeRecord } from '../types';

/** Presentation only: preserve source paths and analytical fingerprints. */
export function technicalPreviewUrl(report: ParkInventoryReport, tree: TreeRecord, kind: 'section' | 'cloud', cacheBust=''): string | null {
  if(report.dataset_kind !== 'simulated')return scanAssetUrl(report.scan_id,kind==='section'?tree.Cross_Section_Image:tree.PointCloud_Preview,cacheBust);
  if(kind==='section')return scanAssetUrl(report.scan_id,`technical-v1/${tree.Tree_ID}-section.svg`,cacheBust);
  return scanAssetUrl(report.scan_id,`technical-v2/${tree.Tree_ID}-cloud.svg`,cacheBust);
}

export function scanAssetUrl(
  scanId: string | null | undefined,
  relative: string | null | undefined,
  cacheBust = "",
): string | null {
  if (!scanId || !relative) return null;
  const clean = relative.replace(/^\.?\//, "");
  return `/scans/${scanId}/${clean}${cacheBust}`;
}
