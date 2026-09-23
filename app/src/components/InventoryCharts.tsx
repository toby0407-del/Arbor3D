import { powerBiChartTables } from "../lib/powerBiCharts";
import type { FieldMeasure } from "../hooks/useFieldMeasures";
import type { ParkInventoryReport } from "../types";

type Props = {
  report: ParkInventoryReport;
  measures: Record<string, FieldMeasure>;
};

export function InventoryCharts({ report, measures }: Props) {
  const { trees, summary, statusChart } = powerBiChartTables(report, measures);
  const maxStatus = Math.max(1, ...statusChart.map((row) => row.count));
  const withDbh = trees
    .filter((row) => row.auto_dbh_cm != null)
    .slice()
    .sort((a, b) => (b.auto_dbh_cm ?? 0) - (a.auto_dbh_cm ?? 0))
    .slice(0, 12);
  const maxDbh = Math.max(1, ...withDbh.map((row) => row.auto_dbh_cm ?? 0));
  const kpi = summary[0];

  return (
    <section className="inv-charts" aria-label="盤點圖表預覽">
      <header className="inv-charts-head">
        <h3>圖表預覽（可匯出至 Power BI）</h3>
        <p>
          KPI：{kpi.observations} 棵 · 配對 {kpi.paired_count} · MAE{" "}
          {kpi.mae_cm == null ? "—" : `${kpi.mae_cm.toFixed(2)} cm`} · CO₂{" "}
          {kpi.co2_ton_total.toFixed(2)} t
          {kpi.dataset_kind === "simulated" ? " · DEMO 模擬" : ""}
        </p>
      </header>
      <div className="inv-charts-grid">
        <figure className="inv-chart-card">
          <figcaption>燈號分布</figcaption>
          <ul className="inv-bar-chart" aria-label="燈號柱狀圖">
            {statusChart.map((row) => (
              <li key={row.color}>
                <span>{row.category}</span>
                <div className="inv-bar-track">
                  <div
                    className={`inv-bar is-${row.color}`}
                    style={{ width: `${(row.count / maxStatus) * 100}%` }}
                  />
                </div>
                <strong>{row.count}</strong>
              </li>
            ))}
          </ul>
        </figure>
        <figure className="inv-chart-card">
          <figcaption>AI 胸徑（前 12 棵）</figcaption>
          <ul className="inv-bar-chart" aria-label="胸徑柱狀圖">
            {withDbh.map((row) => (
              <li key={row.local_tree_id}>
                <span title={row.local_tree_id}>{row.local_tree_id.replace(/^Tree_?/, "T")}</span>
                <div className="inv-bar-track">
                  <div
                    className="inv-bar is-dbh"
                    style={{ width: `${((row.auto_dbh_cm ?? 0) / maxDbh) * 100}%` }}
                  />
                </div>
                <strong>{row.auto_dbh_cm?.toFixed(1)}</strong>
              </li>
            ))}
          </ul>
        </figure>
      </div>
    </section>
  );
}
