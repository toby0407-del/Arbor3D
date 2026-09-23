import type { FieldMeasure } from "../hooks/useFieldMeasures";
import type { ParkInventoryReport } from "../types";
import { analyticsInput, positive } from "./analytics";
import { carbonForTree } from "./carbon";
import { trafficLight } from "./status";

function csvCell(value: string | number | boolean | null | undefined): string {
  let text = value == null || value === false ? "" : value === true ? "true" : String(value);
  if (typeof value === "string" && /^[\s]*[=+@-]/.test(text)) text = `'${text}`;
  if (/[",\r\n]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}

function toCsv(headers: string[], rows: Array<Array<string | number | boolean | null | undefined>>) {
  return `\uFEFF${[headers, ...rows]
    .map((row) => row.map(csvCell).join(","))
    .join("\r\n")}\r\n`;
}

function downloadText(filename: string, content: string, mime: string) {
  const url = URL.createObjectURL(new Blob([content], { type: mime }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Rows tailored for Power BI clustered bar / scatter / KPI cards. */
export function powerBiChartTables(
  report: ParkInventoryReport,
  measures: Record<string, FieldMeasure>,
) {
  const datasetKind = report.dataset_kind === "simulated" ? "simulated" : "observed";
  const trees = report.trees.map((tree) => {
    const field = measures[tree.Tree_ID];
    const carbon = carbonForTree(tree, field, report.created_at);
    const manual = positive(field?.dbhCm);
    const ai = positive(tree.DBH_cm);
    const error = manual != null && ai != null ? ai - manual : null;
    return {
      scan_id: report.scan_id,
      local_tree_id: tree.Tree_ID,
      dataset_kind: datasetKind,
      auto_dbh_cm: ai,
      manual_dbh_cm: manual,
      error_cm: error,
      absolute_error_cm: error == null ? null : Math.abs(error),
      height_m: carbon.heightM,
      co2_ton: carbon.co2Ton,
      status: trafficLight(tree),
      yolo_confidence: tree.YOLO_confidence,
      strict_13m_manual: field?.strict13m === true,
      measured_at: field?.measuredAt || "",
    };
  });

  const paired = trees.filter((row) => row.manual_dbh_cm != null && row.auto_dbh_cm != null);
  const mae =
    paired.length === 0
      ? null
      : paired.reduce((sum, row) => sum + (row.absolute_error_cm ?? 0), 0) / paired.length;
  const statusCounts = {
    green: trees.filter((row) => row.status === "green").length,
    yellow: trees.filter((row) => row.status === "yellow").length,
    red: trees.filter((row) => row.status === "red").length,
  };

  const summary = [
    {
      scope: "all",
      scan_id: report.scan_id,
      dataset_kind: datasetKind,
      observations: trees.length,
      paired_count: paired.length,
      mae_cm: mae,
      review_count: statusCounts.red,
      reliable_count: statusCounts.green,
      pending_count: statusCounts.yellow,
      co2_ton_total: trees.reduce((sum, row) => sum + (row.co2_ton ?? 0), 0),
    },
  ];

  const statusChart = [
    { category: "較可信", count: statusCounts.green, color: "green" },
    { category: "待確認", count: statusCounts.yellow, color: "yellow" },
    { category: "需複核", count: statusCounts.red, color: "red" },
  ];

  return { trees, summary, statusChart };
}

export function downloadPowerBiChartCsvPack(
  report: ParkInventoryReport,
  measures: Record<string, FieldMeasure>,
) {
  const input = analyticsInput(report, measures);
  if (
    input.manual_measurements.some(
      (row) => row.measured_at && !/^\d{4}-\d{2}-\d{2}$/.test(row.measured_at),
    )
  ) {
    alert("請為有人工量測的樹木填寫量測日期（YYYY-MM-DD），再匯出 Power BI 圖表資料。");
    return;
  }

  const { trees, summary, statusChart } = powerBiChartTables(report, measures);
  const stamp = report.scan_id;

  downloadText(
    `${stamp}-ChartTrees.csv`,
    toCsv(
      [
        "scan_id",
        "local_tree_id",
        "dataset_kind",
        "auto_dbh_cm",
        "manual_dbh_cm",
        "error_cm",
        "absolute_error_cm",
        "height_m",
        "co2_ton",
        "status",
        "yolo_confidence",
        "strict_13m_manual",
        "measured_at",
      ],
      trees.map((row) => [
        row.scan_id,
        row.local_tree_id,
        row.dataset_kind,
        row.auto_dbh_cm,
        row.manual_dbh_cm,
        row.error_cm,
        row.absolute_error_cm,
        row.height_m,
        row.co2_ton,
        row.status,
        row.yolo_confidence,
        row.strict_13m_manual,
        row.measured_at,
      ]),
    ),
    "text/csv;charset=utf-8",
  );

  downloadText(
    `${stamp}-ChartSummary.csv`,
    toCsv(
      [
        "scope",
        "scan_id",
        "dataset_kind",
        "observations",
        "paired_count",
        "mae_cm",
        "review_count",
        "reliable_count",
        "pending_count",
        "co2_ton_total",
      ],
      summary.map((row) => [
        row.scope,
        row.scan_id,
        row.dataset_kind,
        row.observations,
        row.paired_count,
        row.mae_cm,
        row.review_count,
        row.reliable_count,
        row.pending_count,
        row.co2_ton_total,
      ]),
    ),
    "text/csv;charset=utf-8",
  );

  downloadText(
    `${stamp}-ChartStatus.csv`,
    toCsv(
      ["category", "count", "color"],
      statusChart.map((row) => [row.category, row.count, row.color]),
    ),
    "text/csv;charset=utf-8",
  );

  downloadText(
    `${stamp}-PowerBI-README.txt`,
    [
      "Arbor3D → Power BI Desktop 圖表匯出",
      "",
      "1. 開啟 Power BI Desktop → 取得資料 → 文字／CSV",
      `2. 載入 ${stamp}-ChartTrees.csv、ChartSummary.csv、ChartStatus.csv`,
      "3. 建議視覺：",
      "   - ChartStatus → 叢集柱狀圖（燈號分布）",
      "   - ChartTrees.auto_dbh_cm vs manual_dbh_cm → 散佈圖（精度）",
      "   - ChartSummary → KPI 卡片（棵數、配對、MAE、CO₂）",
      "   - ChartTrees.co2_ton → 長條圖（單木碳當量）",
      "4. dataset_kind=simulated 時不可當成現場精度成果。",
      "5. 正式五頁 PBIP 請在倉庫根目錄執行：",
      "   python -m powerbi.delivery --bundle <此掃描-powerbi-analytics-input.json> --site-id <site> --out outputs/...",
      "",
      "手測儲存：Azure Cosmos DB FieldMeasures（有設定時）；否則本機 .runtime／localStorage。",
      "盤點本體：App JSON 檔，不寫入 Cosmos。",
      "",
    ].join("\n"),
    "text/plain;charset=utf-8",
  );
}
