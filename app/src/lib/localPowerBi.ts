import { analyticsInput } from './analytics';
import type { FieldMeasure } from '../hooks/useFieldMeasures';
import type { ParkInventoryReport } from '../types';

export type LocalPowerBiSnapshot = {
  schema_version: 1; scan_id: string; dataset_kind: 'observed' | 'simulated';
  input_fingerprint: string; engine: 'Power BI Desktop / Analysis Services';
  calculated_at: string; published_at: string;
  metrics: {
    observations: number; paired_count: number; review_count: number;
    mae_cm: number | null; rmse_cm: number | null; bias_cm: number | null;
    mape_pct: number | null; average_dbh_cm: number | null; co2_ton: number | null;
    demo_pairs: number | null; demo_mae_cm: number | null;
  };
};

export function parseLocalPowerBi(value: unknown, report: ParkInventoryReport): LocalPowerBiSnapshot {
  const data = value as LocalPowerBiSnapshot | null;
  if (!data || data.schema_version !== 1 || data.scan_id !== report.scan_id ||
    data.dataset_kind !== (report.dataset_kind === 'simulated' ? 'simulated' : 'observed') ||
    data.engine !== 'Power BI Desktop / Analysis Services' || !/^[a-f0-9]{64}$/.test(data.input_fingerprint) ||
    !Number.isFinite(Date.parse(data.calculated_at)) || !Number.isFinite(Date.parse(data.published_at)) || !data.metrics) {
    throw new Error('分析結果與目前盤點不符');
  }
  for (const field of ['observations', 'paired_count', 'review_count'] as const) {
    if (!Number.isSafeInteger(data.metrics[field]) || data.metrics[field] < 0) throw new Error('分析計數無效');
  }
  for (const field of ['mae_cm','rmse_cm','bias_cm','mape_pct','average_dbh_cm','co2_ton','demo_pairs','demo_mae_cm'] as const) {
    const n = data.metrics[field];
    if (n !== null && (typeof n !== 'number' || !Number.isFinite(n))) throw new Error('分析數值無效');
  }
  if (data.metrics.observations !== report.trees.length || data.metrics.paired_count > data.metrics.observations ||
    data.metrics.review_count > data.metrics.observations ||
    (data.metrics.paired_count === 0 && [data.metrics.mae_cm,data.metrics.rmse_cm,data.metrics.bias_cm,data.metrics.mape_pct].some(n=>n!==null)) ||
    (data.dataset_kind === 'simulated' && data.metrics.paired_count !== 0)) throw new Error('分析配對條件無效');
  return data;
}

export function analyticsFingerprintText(report: ParkInventoryReport, measures: Record<string, FieldMeasure>) {
  const canonical=(value:unknown):unknown=>Array.isArray(value)?value.map(canonical):
    value && typeof value==='object'?Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b,'en')).map(([k,v])=>[k,canonical(v)])):value;
  return JSON.stringify(canonical(analyticsInput(report, measures)));
}
export async function currentAnalyticsFingerprint(report: ParkInventoryReport, measures: Record<string, FieldMeasure>) {
  const bytes = new TextEncoder().encode(analyticsFingerprintText(report, measures));
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b=>b.toString(16).padStart(2,'0')).join('');
}
