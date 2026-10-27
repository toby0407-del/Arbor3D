import type { FieldMeasure } from "../hooks/useFieldMeasures";
import type { MeasurementQuality, ParkInventoryReport, TreeRecord } from "../types";

export const qualityReasons: Record<string, string> = {
  scale_verified_required: "待確認實際尺度", pose_verified_required: "待確認相機姿態",
  breast_height_verified_required: "待確認胸高基準", insufficient_geometry: "獨立幾何點不足",
  unstable_circle_geometry: "圓參數不穩定", view_direction_verified_required: "卡尺方向尚未確認",
  left_boundary_visible_required: "左側切向邊界待確認", right_boundary_visible_required: "右側切向邊界待確認",
  near_circular_verified_required: "幹形近圓條件待確認", uncropped_boundaries_required: "邊界可能遮擋或截斷",
  missing_calibration: "尚無人工真值校準模型", independent_validation_required: "獨立測試尚未達驗收條件",
  missing_features: "品質特徵不足", outside_calibration_domain: "超出校準資料適用範圍",
  precision_target_not_met: "校準達標機率不足", candidate_outside_size_range: "候選尺寸超出研究範圍",
  disconnected_section: "截面不連續", calibration_scope_mismatch: "設備或處理規範不符模型適用範圍",
};

export function qualityAccepted(q: MeasurementQuality | null | undefined): boolean {
  return !!q && (q.method === "circle" || q.method === "caliper") && q.schema_version === "arbor3d-quality-1" && q.decision === "accepted" &&
    q.identifiable === true && !!q.model_id && Array.isArray(q.reasons) && q.reasons.length === 0 &&
    typeof q.probability === "number" && Number.isFinite(q.probability) && q.probability <= 1 &&
    Number.isFinite(q.target_probability) && q.target_probability > 0 && q.target_probability < 1 &&
    q.probability >= q.target_probability && typeof q.tolerance_cm === "number" && q.tolerance_cm > 0;
}

export type ViewCandidate = { azimuth_deg: number; new_coverage_deg: number; time_s: number; safe: boolean; reachable: boolean };
export function rankViews(candidates: ViewCandidate[]) {
  return candidates.filter(c => c.safe === true && c.reachable === true &&
    [c.azimuth_deg, c.new_coverage_deg, c.time_s].every(Number.isFinite) &&
    c.azimuth_deg >= 0 && c.azimuth_deg < 360 && c.new_coverage_deg > 0 && c.new_coverage_deg <= 360 && c.time_s > 0)
    .map(c => ({ ...c, score: c.new_coverage_deg / c.time_s }))
    .sort((a,b) => b.score - a.score || a.azimuth_deg - b.azimuth_deg);
}

export function qualityEvidence(report: ParkInventoryReport, measures: Record<string, FieldMeasure>) {
  return { schema_version: "arbor3d-quality-evidence-1", scope: {sensor_id: "", protocol_id: ""},
    notice: "先確認固定樹號、設備/規範與互斥分組；缺失特徵保持空白。模擬資料不能校準真實精度。",
    rows: report.trees.flatMap(tree => {
      const field = measures[tree.Tree_ID];
      const candidates = tree.quality_candidates?.length ? tree.quality_candidates :
        [{ ...tree.measurement_quality, method: tree.DBH_method, candidate_dbh_cm: tree.candidate_dbh_cm ?? tree.DBH_cm }];
      return candidates.map(c => ({ source: report.dataset_kind === "simulated" || tree.dataset_kind === "simulated" || report.scan_id.startsWith("sim") ? "simulated" : "observed",
        scan_id: report.scan_id, tree_id: tree.Tree_ID, persistent_tree_id: tree.persistent_tree_id ?? "",
        split: "unassigned", method: c.method, candidate_dbh_cm: c.candidate_dbh_cm,
        manual_dbh_cm: field?.dbhCm?.trim() && Number(field.dbhCm) > 0 ? Number(field.dbhCm) : null,
        scan_date: report.created_at.slice(0,10), manual_date: field?.measuredAt ?? "", strict_13m: field?.strict13m === true,
        features: c.features ?? {}, context: c.context ?? {} }));
    }) };
}

export function qualityState(tree: TreeRecord): string {
  if (!tree.measurement_quality) return "歷史結果 · 尚無多指標品質紀錄";
  return qualityAccepted(tree.measurement_quality) && tree.dbh_is_strict_breast_height && tree.DBH_cm != null && tree.DBH_cm > 0
    ? "通過方法專屬品質門檻" : "待補掃或人工複核";
}

export function downloadJson(value: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], {type: "application/json"}));
  const a = document.createElement("a"); a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
