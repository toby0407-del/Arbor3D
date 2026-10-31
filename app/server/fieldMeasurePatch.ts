import type { FieldMeasureRecord } from "./fieldMeasureStore.js";

export type MeasurePatch = Partial<FieldMeasureRecord[string]>;
const fields = new Set(["dbhCm", "heightM", "coeff", "measuredAt", "note", "strict13m"]);
export function validMeasureId(value: unknown): value is string {
  return typeof value === "string" && /^[\w.-]{1,100}$/.test(value) && !["__proto__", "constructor", "prototype"].includes(value);
}

export function validMeasurePatch(value: unknown): value is MeasurePatch {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const entries = Object.entries(value);
  return entries.length > 0 && entries.every(([key, item]) => fields.has(key) && (
    key === "strict13m" ? typeof item === "boolean"
      : typeof item === "string" && item.length <= (key === "note" ? 500 : 40)
  ));
}

export function applyMeasurePatch(measures: FieldMeasureRecord, treeId: string, patch: MeasurePatch): FieldMeasureRecord {
  return { ...measures, [treeId]: {
    ...(measures[treeId] ?? { dbhCm: "", heightM: "", coeff: "", measuredAt: "", note: "", strict13m: false }), ...patch,
  } };
}
