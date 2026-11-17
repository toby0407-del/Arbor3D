/** Keep measured candidates separate from unmeasurable detections. No padding. */
export function partitionMeasuredRecords(records) {
  const measured = [], excluded = [];
  for (const record of records) {
    (typeof record.DBH_cm === "number" && Number.isFinite(record.DBH_cm) && record.DBH_cm > 0
      ? measured : excluded).push(record);
  }
  return { measured, excluded };
}
