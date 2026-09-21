import type { FieldMeasure } from '../hooks/useFieldMeasures';
import type { ParkInventoryReport } from '../types';

export const sourceLabel = (source: string) => source === 'measured' ? '人工實測' : source === 'ai' ? 'AI／演算法結果' : '推估／模擬';
export function positive(value: unknown): number | null {
  if (value === '' || value == null || typeof value === 'boolean') return null;
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : null;
}
export function analyticsInput(report: ParkInventoryReport, measures: Record<string, FieldMeasure>) {
  return {
    schema_version: '1.0',
    report,
    manual_measurements: report.trees.flatMap(tree => {
      const field = measures[tree.Tree_ID];
      if (!field || (positive(field.dbhCm) === null && positive(field.heightM) === null)) return [];
      return [{ scan_id: report.scan_id, local_tree_id: tree.Tree_ID,
        manual_dbh_cm: positive(field.dbhCm), manual_height_m: positive(field.heightM), carbon_coefficient: positive(field.coeff),
        measured_at: field.measuredAt || '', strict_13m: field.strict13m === true }];
    }),
  };
}
export function downloadAnalyticsInput(report: ParkInventoryReport, measures: Record<string, FieldMeasure>) {
  const data = analyticsInput(report, measures);
  if (data.manual_measurements.some(row => !/^\d{4}-\d{2}-\d{2}$/.test(row.measured_at))) {
    alert('請為有人工量測的樹木填寫量測日期（YYYY-MM-DD），再匯出分析資料。');
    return;
  }
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'}));
  const a = document.createElement('a');
  a.href = url; a.download = `${report.scan_id}-analytics-input.json`; a.click();
  URL.revokeObjectURL(url);
}
