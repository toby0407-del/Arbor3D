import type { TrafficLight, TreeRecord } from "../types";
import { qualityAccepted, qualityReasons } from "./measurementQuality";

export type InventoryStats = {
  total: number;
  green: number;
  yellow: number;
  red: number;
  review: number;
  avgConfidence: number | null;
};

export function trafficLight(input: TreeRecord | string | null | undefined): TrafficLight {
  const tree = typeof input === "object" && input !== null ? input : null;
  const value = tree ? tree.DBH_note ?? "" : typeof input === "string" ? input : "";
  if (tree?.measurement_quality && !qualityAccepted(tree.measurement_quality)) return "red";
  if (tree && (tree.DBH_cm == null || !Number.isFinite(tree.DBH_cm) || tree.DBH_cm <= 0 ||
    (tree.DBH_method === "caliper" && tree.DBH_cm >= 45))) return "red";
  if (
    value === "no_measurement" ||
    value.includes("wide_caliper") ||
    value.includes("gap")
  ) {
    return "red";
  }
  if (tree?.dataset_kind === 'simulated' && (tree.scenario_review_required === true || value.includes('negative_review'))) return 'red';
  const notes = value.split(',').filter(Boolean).filter(note => note !== 'ok' &&
    !(tree?.dataset_kind === 'simulated' && ['模擬資料','steady','slow','stalled','simulated_steady','simulated_slow','simulated_stalled'].includes(note)));
  if ((tree && tree.dbh_is_strict_breast_height !== true) || notes.length) return "yellow";
  return "green";
}

export function lightLabel(light: TrafficLight): string {
  if (light === "green") return "演算法較可信";
  if (light === "yellow") return "有數字，建議現場核對";
  return "卡尺偏寬或量不到，現場再量";
}

export function lightShort(light: TrafficLight): string {
  if (light === "green") return "可信";
  if (light === "yellow") return "需核對";
  return "需複核";
}

export function reviewReason(tree: TreeRecord): string {
  const notes = (tree.DBH_note || "").split(",").filter(Boolean);
  const parts: string[] = [];
  if (tree.dataset_kind === 'simulated' && (tree.scenario_review_required === true || notes.some(n=>n.includes('negative_review')))) parts.push('跨期變化異常，需核對');
  if (tree.measurement_quality && !qualityAccepted(tree.measurement_quality)) {
    parts.push(...(tree.measurement_quality.reasons ?? []).map(r => qualityReasons[r] ?? "品質條件待複核"));
  }
  if (!tree.dbh_is_strict_breast_height) parts.push("非標準 1.3 m，需現場確認");
  if (notes.includes("wide_caliper") || (tree.DBH_method === "caliper" && (tree.DBH_cm ?? 0) >= 45)) parts.push("卡尺偏寬");
  if (notes.includes("gap")) parts.push("切片有缺口");
  if (notes.includes("no_measurement") || tree.DBH_cm == null || !(tree.DBH_cm > 0)) parts.push("量不到");
  if (tree.arc_coverage_deg != null) parts.push(`弧度 ${tree.arc_coverage_deg.toFixed(1)}°（需聯合其他品質特徵）`);
  return parts.join(" · ") || "需現場再量";
}

export function isReviewTree(tree: TreeRecord): boolean {
  return trafficLight(tree) !== "green";
}

export function noteLabel(tree: TreeRecord): string {
  const reason = reviewReason(tree);
  if (trafficLight(tree) === "green") return "通過";
  return reason;
}

export function inventoryStats(trees: TreeRecord[]): InventoryStats {
  let green = 0;
  let yellow = 0;
  let red = 0;
  let confSum = 0;
  let confN = 0;
  for (const tree of trees) {
    const light = trafficLight(tree);
    if (light === "green") green += 1;
    else if (light === "yellow") yellow += 1;
    else red += 1;
    if (tree.YOLO_confidence != null) {
      confSum += tree.YOLO_confidence;
      confN += 1;
    }
  }
  return {
    total: trees.length,
    green,
    yellow,
    red,
    review: trees.filter(isReviewTree).length,
    avgConfidence: confN ? confSum / confN : null,
  };
}
