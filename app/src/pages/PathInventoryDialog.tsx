import { downloadAnalyticsInput, sourceLabel } from "../lib/analytics";
import { useEffect, useMemo, useRef, useState } from "react";
import { PathTreeMap } from "../components/PathTreeMap";
import { PlyViewer } from "../components/PlyViewer";
import { InventoryAssistant } from "../components/InventoryAssistant";
import { useBodyScrollLock } from "../hooks/useBodyScrollLock";
import { useModalTouchScrollLock } from "../hooks/useModalTouchScrollLock";
import { useFieldMeasures } from "../hooks/useFieldMeasures";
import {
  CARBON_COEFFS,
  carbonForTree,
  coeffSelectValue,
  isCustomCoeff,
  totalCo2Ton,
} from "../lib/carbon";
import { downloadInventoryCsv } from "../lib/csv";
import {
  breastHeightLabel,
  formatArc,
  formatConfidence,
  formatDbh,
  formatScanTime,
  formatXyz,
  methodLabel,
} from "../lib/format";
import { scanAssetUrl } from "../lib/scanMedia";
import {
  availableYears,
  defaultGrowthRange,
  filterPointsByRange,
  formatAxisMonthYear,
  formatRangeTitle,
  formatScanMonthDay,
  growthStatusLabel,
  shiftGrowthRange,
  temporalGrowth,
  type GrowthPoint,
  type GrowthRange,
  type GrowthRangeMode,
  type GrowthStatus,
  type TemporalGrowth,
} from "../lib/growth";
import {
  inventoryStats,
  isReviewTree,
  reviewReason,
  trafficLight,
} from "../lib/status";
import type { ParkInventoryReport, TrafficLight, TreeRecord } from "../types";

type PreviewTab = "images" | "measure" | "model";
type Filter = "all" | TrafficLight | "review";

function TreeGlyph() {
  return (
    <svg viewBox="0 0 20 20" width="17" height="17" aria-hidden="true">
      <path
        d="M10 1.4C6.6 1.4 4.2 4.4 4.8 7.4 2.2 7.8 1.3 10.8 3.6 12.6h12.8c2.3-1.8 1.4-4.8-1.2-5.2C15.8 4.4 13.4 1.4 10 1.4Z"
        fill="currentColor"
      />
      <path d="M8.55 12.4h2.9V18H8.55z" fill="#5a3814" />
      <path
        d="M4.4 18.35h11.2"
        fill="none"
        stroke="#5a3814"
        strokeWidth="1.35"
        strokeLinecap="round"
      />
    </svg>
  );
}

function GrowthIconButton({
  status,
  onClick,
}: {
  status: GrowthStatus;
  onClick: () => void;
}) {
  const label = growthStatusLabel(status);
  const fit =
    status === "abnormal" ? "off" : status === "normal" ? "ok" : "watch";
  return (
    <button
      type="button"
      className={`growth-icon-btn is-${fit}`}
      title={label}
      aria-label={label}
      onClick={(event) => {
        event.stopPropagation();
        onClick();
      }}
    >
      <TreeGlyph />
    </button>
  );
}

function GrowthTrendPopup({
  treeId,
  scanCreatedAt,
  temporal,
  onClose,
}: {
  treeId: string;
  scanCreatedAt: string;
  temporal: TemporalGrowth;
  onClose: () => void;
}) {
  const { previous, current, trend, points, status } = temporal;
  const snaps = [previous, current, trend];
  const years = availableYears(points);
  const [mode, setMode] = useState<GrowthRangeMode>("year");
  const [range, setRange] = useState<GrowthRange>(() =>
    defaultGrowthRange("year", scanCreatedAt),
  );

  const setModeAndRange = (next: GrowthRangeMode) => {
    setMode(next);
    setRange(defaultGrowthRange(next, scanCreatedAt));
  };

  const visible = useMemo(
    () => filterPointsByRange(points, range),
    [points, range],
  );

  const chartW = 640;
  const chartH = 220;
  const pad = { l: 48, r: 16, t: 16, b: 42 };
  const values = visible.map((point) => point.dbhCm);
  const min = (values.length ? Math.min(...values) : 0) - 0.6;
  const max = (values.length ? Math.max(...values) : 1) + 0.6;
  const span = Math.max(0.8, max - min);
  const xy = (point: GrowthPoint, index: number) => {
    const x =
      pad.l +
      (index / Math.max(1, visible.length - 1)) * (chartW - pad.l - pad.r);
    const y =
      pad.t + (1 - (point.dbhCm - min) / span) * (chartH - pad.t - pad.b);
    return { x, y };
  };
  const coords = visible.map(xy);
  const line = coords
    .map(
      (pt, index) =>
        `${index === 0 ? "M" : "L"}${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`,
    )
    .join(" ");
  const baseY = chartH - pad.b;
  const area =
    coords.length > 0
      ? `${line} L${coords[coords.length - 1].x.toFixed(1)} ${baseY} L${coords[0].x.toFixed(1)} ${baseY} Z`
      : "";
  const labelStep = Math.max(1, Math.ceil(visible.length / 8));
  const tone =
    status === "abnormal" ? "red" : status === "normal" ? "green" : "yellow";

  return (
    <div
      className="growth-backdrop"
      role="presentation"
      onClick={(event) => {
        event.stopPropagation();
        onClose();
      }}
    >
      <div
        className="growth-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="growth-pop-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="growth-head">
          <div>
            <p className="growth-kicker">
              {treeId} · {formatScanMonthDay(scanCreatedAt)}
            </p>
            <h2 id="growth-pop-title">時序成長</h2>
          </div>
          <div className="growth-head-actions">
            <span className={`growth-status pill is-${tone}`}>
              <TreeGlyph />
              {growthStatusLabel(status)}
            </span>
            <button type="button" className="ghost-btn" onClick={onClose}>
              關閉
            </button>
          </div>
        </header>

        <div className="growth-body">
          <ol className="growth-snaps">
            {snaps.map((snap, index) => {
              const prior = index === 0 ? null : snaps[index - 1].dbhCm;
              const delta = prior == null ? null : snap.dbhCm - prior;
              const deltaText =
                delta == null
                  ? "基準"
                  : Math.abs(delta) < 0.005
                    ? "Δ 0.00 cm"
                    : `Δ ${delta > 0 ? "+" : ""}${delta.toFixed(2)} cm`;
              return (
                <li key={snap.role} className={`growth-snap is-${snap.role}`}>
                  <span className="growth-snap-role">{snap.roleLabel}</span>
                  <strong className="growth-snap-value">
                    {snap.dbhCm.toFixed(2)}
                    <em>cm</em>
                  </strong>
                  <span className="growth-snap-period">{snap.periodLabel} · {sourceLabel(snap.source)}</span>
                  <span className="growth-snap-delta">{deltaText}</span>
                </li>
              );
            })}
          </ol>

          <div className="growth-range-bar">
            <div className="growth-range-modes" role="tablist" aria-label="時區">
              {(
                [
                  ["year", "每年"],
                  ["quarter", "每季"],
                  ["custom", "自訂"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={mode === id}
                  className={`growth-range-mode${mode === id ? " is-on" : ""}`}
                  onClick={() => setModeAndRange(id)}
                >
                  {label}
                </button>
              ))}
            </div>

            {mode === "custom" ? (
              <div className="growth-custom-range">
                <label>
                  起
                  <select
                    value={`${range.from.year}-${range.from.month}`}
                    onChange={(event) => {
                      const [y, m] = event.target.value.split("-").map(Number);
                      setRange((prev) => ({
                        ...prev,
                        mode: "custom",
                        from: { year: y, month: m },
                      }));
                    }}
                  >
                    {points.map((p) => (
                      <option
                        key={`from-${p.year}-${p.month}`}
                        value={`${p.year}-${p.month}`}
                      >
                        {p.year}/{p.month}
                      </option>
                    ))}
                  </select>
                </label>
                <span aria-hidden="true">→</span>
                <label>
                  迄
                  <select
                    value={`${range.to.year}-${range.to.month}`}
                    onChange={(event) => {
                      const [y, m] = event.target.value.split("-").map(Number);
                      setRange((prev) => ({
                        ...prev,
                        mode: "custom",
                        to: { year: y, month: m },
                      }));
                    }}
                  >
                    {points.map((p) => (
                      <option
                        key={`to-${p.year}-${p.month}`}
                        value={`${p.year}-${p.month}`}
                      >
                        {p.year}/{p.month}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            ) : (
              <div className="growth-range-nav">
                <button
                  type="button"
                  className="ghost-btn"
                  aria-label="上一時區"
                  onClick={() => setRange((prev) => shiftGrowthRange(prev, -1))}
                >
                  ‹
                </button>
                <strong>{formatRangeTitle(range)}</strong>
                <button
                  type="button"
                  className="ghost-btn"
                  aria-label="下一時區"
                  onClick={() => setRange((prev) => shiftGrowthRange(prev, 1))}
                >
                  ›
                </button>
              </div>
            )}
          </div>

          <figure className="growth-chart-wrap">
            <figcaption>
              {formatRangeTitle(range)} · 胸徑趨勢（橫軸：年／月）
            </figcaption>
            <svg
              className="growth-chart"
              viewBox={`0 0 ${chartW} ${chartH}`}
              role="img"
              aria-label={`${treeId} 胸徑趨勢`}
            >
              {[0, 0.5, 1].map((t) => {
                const y = pad.t + (1 - t) * (chartH - pad.t - pad.b);
                const label = min + span * t;
                return (
                  <g key={t}>
                    <line
                      x1={pad.l}
                      x2={chartW - pad.r}
                      y1={y}
                      y2={y}
                      className="growth-grid"
                    />
                    <text x={pad.l - 10} y={y + 4} className="growth-axis is-y">
                      {label.toFixed(1)}
                    </text>
                  </g>
                );
              })}
              {area ? <path d={area} className="growth-area" /> : null}
              {line ? <path d={line} className="growth-line is-sim-line" /> : null}
              {coords.map((pt, index) => {
                const point = visible[index];
                const real = point.source !== "sim";
                const showLabel =
                  real || index % labelStep === 0 || index === visible.length - 1;
                return (
                  <g key={`${point.year}-${point.month}-${point.source}`}>
                    <circle
                      cx={pt.x}
                      cy={pt.y}
                      r={real ? 6 : 3.5}
                      className={`growth-dot is-${point.source === "sim" ? "sim" : "real"}`}
                    >
                      <title>
                        {formatAxisMonthYear(point)} · {point.dbhCm.toFixed(2)}{" "}
                        cm · {sourceLabel(point.source)}
                      </title>
                    </circle>
                    {showLabel ? (
                      <text
                        x={pt.x}
                        y={chartH - 12}
                        textAnchor="middle"
                        className={`growth-axis${real ? " is-on" : ""}`}
                      >
                        {formatAxisMonthYear(point)}
                      </text>
                    ) : null}
                  </g>
                );
              })}
            </svg>
          </figure>

          <p className="growth-foot">
            推估情境，非跨期實測趨勢。{temporal.carbonNote}
            {years.length > 0
              ? `　·　序列 ${years[0]}–${years[years.length - 1]}`
              : null}
          </p>
        </div>
      </div>
    </div>
  );
}

function temporalForTree(
  tree: TreeRecord,
  field: { dbhCm?: string; measuredAt?: string } | undefined,
  carbon: { heightM: number | null; heightEstimated: boolean },
  scanIso: string,
): TemporalGrowth | null {
  const dbh =
    Number(field?.dbhCm) > 0 ? Number(field?.dbhCm) : tree.DBH_cm;
  if (dbh == null || !(dbh > 0)) return null;
  return temporalGrowth({
    dbhCm: dbh,
    heightM: carbon.heightM,
    heightEstimated: carbon.heightEstimated,
    scanIso: Number(field?.dbhCm) > 0 && field?.measuredAt ? field.measuredAt : scanIso,
    baseSource: Number(field?.dbhCm) > 0 ? "measured" : "ai",
    note: tree.DBH_note,
    yoloConfidence: tree.YOLO_confidence,
  });
}

function FormulaPopup({ onClose }: { onClose: () => void }) {
  return (
    <div className="formula-popup-backdrop" role="presentation" onClick={onClose}>
      <div
        className="formula-popup"
        role="dialog"
        aria-modal="true"
        aria-labelledby="formula-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <strong id="formula-title">碳量估算公式</strong>
          <button type="button" className="ghost-btn" onClick={onClose}>
            關閉
          </button>
        </header>
        <table className="formula-table">
          <tbody>
            <tr>
              <td><strong>A</strong></td>
              <td>高度 1.3 m 處圓周（m）</td>
              <td><code>π × 胸徑(m)</code></td>
            </tr>
            <tr>
              <td><strong>B</strong></td>
              <td>樹高（m）</td>
              <td>實測 or 粗估 <code>1.3 + 1.8√DBH</code></td>
            </tr>
            <tr>
              <td><strong>C</strong></td>
              <td>係數</td>
              <td>預設 <code>0.0159</code>（表定）</td>
            </tr>
            <tr>
              <td><strong>D</strong></td>
              <td>樹含碳量</td>
              <td><code>A² × B × C</code></td>
            </tr>
            <tr>
              <td><strong>CO₂</strong></td>
              <td>估算 CO₂ 當量（ton）</td>
              <td><code>D × 3.667</code></td>
            </tr>
          </tbody>
        </table>
        <p className="formula-note">
          係數 C 可選：表定 0.0159 ／闊葉 0.027 ／針葉 0.020 ／自訂。<br />
          3.667 = CO₂ 與 C 的分子量比（44÷12）。
        </p>
      </div>
    </div>
  );
}

type Props = {
  parkName: string;
  pathName: string;
  report: ParkInventoryReport;
  previewTreeId: string | null;
  onPreviewTree: (treeId: string) => void;
  onClose: () => void;
  onImport?: () => void;
};

function ZoomImage({
  src,
  title,
  alt,
  onOpen,
}: {
  src: string;
  title: string;
  alt: string;
  onOpen: () => void;
}) {
  const [ok, setOk] = useState(true);
  useEffect(() => {
    setOk(true);
  }, [src]);
  if (!ok) {
    return <div className="path-db-empty">尚無{title}</div>;
  }
  return (
    <button type="button" className="path-db-thumb" onClick={onOpen}>
      <img src={src} alt={alt} onError={() => setOk(false)} />
      <span>點擊放大</span>
    </button>
  );
}

export function PathInventoryDialog({
  parkName,
  pathName,
  report,
  previewTreeId,
  onPreviewTree,
  onClose,
  onImport,
}: Props) {
  useBodyScrollLock();
  const panelRef = useRef<HTMLDivElement | null>(null);
  useModalTouchScrollLock(panelRef);
  const [lightbox, setLightbox] = useState<{ src: string; title: string } | null>(
    null,
  );
  const [showFormula, setShowFormula] = useState(false);
  const [showAssistant, setShowAssistant] = useState(false);
  const [growthTreeId, setGrowthTreeId] = useState<string | null>(null);
  const [tab, setTab] = useState<PreviewTab>("images");
  const [filter, setFilter] = useState<Filter>("all");
  const { measures, update } = useFieldMeasures(report.scan_id);
  const stats = useMemo(() => inventoryStats(report.trees), [report.trees]);
  const co2Total = useMemo(
    () => totalCo2Ton(report.trees, measures, report.created_at),
    [measures, report.created_at, report.trees],
  );
  const visible = useMemo(() => {
    return report.trees.filter((tree) => {
      if (filter === "all") return true;
      if (filter === "review") return isReviewTree(tree);
      return trafficLight(tree) === filter;
    });
  }, [filter, report.trees]);

  const growthById = useMemo(() => {
    const map = new Map<string, TemporalGrowth>();
    for (const tree of report.trees) {
      const carbon = carbonForTree(
        tree,
        measures[tree.Tree_ID],
        report.created_at,
      );
      const temporal = temporalForTree(
        tree,
        measures[tree.Tree_ID],
        carbon,
        report.created_at,
      );
      if (temporal) map.set(tree.Tree_ID, temporal);
    }
    return map;
  }, [measures, report.created_at, report.trees]);

  const growthTree = growthTreeId
    ? report.trees.find((tree) => tree.Tree_ID === growthTreeId)
    : null;
  const growthTemporal = growthTreeId
    ? growthById.get(growthTreeId) ?? null
    : null;

  const preview =
    visible.find((tree) => tree.Tree_ID === previewTreeId) ??
    visible[0] ??
    report.trees[0] ??
    null;

  useEffect(() => {
    if (preview && preview.Tree_ID !== previewTreeId) {
      onPreviewTree(preview.Tree_ID);
    }
  }, [onPreviewTree, preview, previewTreeId]);

  useEffect(() => {
    panelRef.current
      ?.querySelector("tr.is-active")
      ?.scrollIntoView({ block: "nearest" });
  }, [preview?.Tree_ID]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (growthTreeId) {
          setGrowthTreeId(null);
          return;
        }
        if (showAssistant) {
          setShowAssistant(false);
          return;
        }
        if (showFormula) {
          setShowFormula(false);
          return;
        }
        if (lightbox) {
          setLightbox(null);
          return;
        }
        onClose();
        return;
      }
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
      event.preventDefault();
      if (visible.length === 0) return;
      const current = preview?.Tree_ID ?? visible[0].Tree_ID;
      const idx = visible.findIndex((tree) => tree.Tree_ID === current);
      const next =
        event.key === "ArrowDown"
          ? visible[(idx + 1) % visible.length]
          : visible[(idx - 1 + visible.length) % visible.length];
      onPreviewTree(next.Tree_ID);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [growthTreeId, lightbox, onClose, onPreviewTree, preview, showAssistant, showFormula, visible]);

  const cacheBust = `?t=${encodeURIComponent(report.created_at)}`;
  const maskUrl = preview
    ? scanAssetUrl(report.scan_id, preview.Mask_Path, cacheBust)
    : null;
  const sliceUrl = preview
    ? scanAssetUrl(report.scan_id, preview.Cross_Section_Image, cacheBust)
    : null;
  const photoUrl = preview
    ? scanAssetUrl(report.scan_id, preview.Best_Photo, cacheBust)
    : null;
  const cloudPreviewUrl = preview
    ? scanAssetUrl(report.scan_id, preview.PointCloud_Preview, cacheBust)
    : null;
  const hasModel = Boolean(preview?.Single_Tree_Ply);
  const modelUrl =
    preview && hasModel
      ? scanAssetUrl(report.scan_id, preview.Single_Tree_Ply)
      : null;

  useEffect(() => {
    if (tab === "model" && !hasModel) setTab("images");
  }, [hasModel, tab]);
  const field = preview ? measures[preview.Tree_ID] : undefined;
  const light = preview ? trafficLight(preview) : "red";
  const carbon = preview
    ? carbonForTree(preview, field, report.created_at)
    : null;

  return (
    <div className="path-db-backdrop" role="presentation" onClick={onClose}>
      <div
        className="path-db-panel is-wide"
        role="dialog"
        aria-modal="true"
        aria-labelledby="path-db-title"
        ref={panelRef}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="path-db-head">
          <div>
            <p className="path-db-kicker">{parkName}</p>
            <h2 id="path-db-title">{pathName}</h2>
            <p>{formatScanTime(report.created_at)}</p>
            <div className="inv-summary" aria-label="盤點摘要">
              <span className="pill">{stats.total} 棵</span>
              {stats.green > 0 ? (
                <span className="pill is-green">較可信 {stats.green}</span>
              ) : null}
              {stats.yellow > 0 ? (
                <span className="pill is-yellow">待確認 {stats.yellow}</span>
              ) : null}
              {stats.red > 0 ? (
                <span className="pill is-red">需複核 {stats.red}</span>
              ) : null}
              <span className="pill">
                平均信心 {formatConfidence(stats.avgConfidence)}
              </span>
              <span className="pill is-green">
                估算 CO₂ 當量 {co2Total.toFixed(2)} ton
              </span>
            </div>
          </div>
          <div className="path-db-head-actions">
            <button
              type="button"
              className="primary-btn"
              onClick={() => setShowAssistant(true)}
            >
              詢問 AI 助理
            </button>
            <button
              type="button"
              className="formula-btn"
              title="碳量估算公式說明"
              aria-label="碳量估算公式說明"
              onClick={() => setShowFormula(true)}
            >
              ?
            </button>
            <button
              type="button"
              className="ghost-btn"
              onClick={() =>
                downloadInventoryCsv(
                  report.trees,
                  measures,
                  `${report.scan_id}-inventory.csv`,
                  report.created_at,
                )
              }
            >
              匯出 CSV
            </button>
            <button type="button" className="ghost-btn" onClick={() => downloadAnalyticsInput(report, measures)}>匯出分析資料</button>
            {onImport ? (
              <button type="button" className="ghost-btn" onClick={onImport}>
                再匯入
              </button>
            ) : null}
            <button type="button" className="ghost-btn" onClick={onClose}>
              關閉
            </button>
          </div>
        </header>

        <div className="path-db-body">
          <aside className="path-db-map">
            <h3>路徑圖</h3>
            <PathTreeMap
              trees={report.trees}
              selectedId={preview?.Tree_ID ?? null}
              onPick={onPreviewTree}
            />
          </aside>

          <div
            className="path-db-table-wrap"
          >
            <div className="inv-filters" role="tablist" aria-label="篩選">
              {(
                [
                  ["all", `全部 ${stats.total}`, stats.total],
                  ["green", `較可信 ${stats.green}`, stats.green],
                  ["yellow", `待確認 ${stats.yellow}`, stats.yellow],
                  ["red", `需複核 ${stats.red}`, stats.red],
                  ["review", `待複核 ${stats.review}`, stats.review],
                ] as const
              )
                .filter(([id, , count]) => id === "all" || count > 0)
                .map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={filter === id}
                  className={`kind-tab ${filter === id ? "is-active" : ""}`}
                  onClick={() => setFilter(id)}
                >
                  {label}
                </button>
              ))}
            </div>
            {visible.length === 0 ? (
              <div className="path-db-empty">這個篩選沒有樹</div>
            ) : (
              <table className="compact-tree-table">
                <thead>
                  <tr>
                    <th>樹號</th>
                    <th>AI 胸徑</th>
                    <th>樹高</th>
                    <th>估算 CO₂ 當量</th>
                    <th className="growth-col">健康度</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((tree) => {
                    const rowLight = trafficLight(tree);
                    const active = tree.Tree_ID === preview?.Tree_ID;
                    const row = carbonForTree(
                      tree,
                      measures[tree.Tree_ID],
                      report.created_at,
                    );
                    const temporal = growthById.get(tree.Tree_ID);
                    return (
                      <tr
                        key={tree.Tree_ID}
                        className={`is-${rowLight}${active ? " is-active" : ""}`}
                        tabIndex={0}
                        aria-selected={active}
                        onClick={() => onPreviewTree(tree.Tree_ID)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            onPreviewTree(tree.Tree_ID);
                          }
                        }}
                      >
                        <td className="mono">{tree.Tree_ID.replace("Tree_", "#")}</td>
                        <td>{formatDbh(tree.DBH_cm)}</td>
                        <td>
                          {row.heightM != null
                            ? row.heightEstimated
                              ? `${row.heightM.toFixed(1)} m（估）`
                              : `${row.heightM.toFixed(1)} m`
                            : "—"}
                        </td>
                        <td>{row.co2Ton != null ? `${row.co2Ton.toFixed(3)} t` : "—"}</td>
                        <td className="growth-col">
                          {temporal ? (
                            <GrowthIconButton
                              status={temporal.status}
                              onClick={() => {
                                onPreviewTree(tree.Tree_ID);
                                setGrowthTreeId(tree.Tree_ID);
                              }}
                            />
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={3}>合計</td>
                    <td>
                      <strong>
                        {`${visible
                          .reduce((sum, tree) => {
                            const r = carbonForTree(
                              tree,
                              measures[tree.Tree_ID],
                              report.created_at,
                            );
                            return sum + (r.co2Ton ?? 0);
                          }, 0)
                          .toFixed(3)} t`}
                      </strong>
                    </td>
                    <td className="growth-col" />
                  </tr>
                </tfoot>
              </table>
            )}
          </div>

          <aside className="path-db-preview">
            <div className="inv-tabs" role="tablist" aria-label="樹身分">
              {(
                [
                  ["images", "影像"],
                  ["measure", "量測"],
                  ["model", "3D"],
                ] as const
              )
                .filter(([id]) => id !== "model" || hasModel)
                .map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={tab === id}
                  className={`kind-tab ${tab === id ? "is-active" : ""}`}
                  onClick={() => setTab(id)}
                >
                  {label}
                </button>
              ))}
            </div>

            {!preview ? (
              <div className="path-db-empty">尚無盤點資料</div>
            ) : tab === "images" ? (
              <>
                <h3>
                  {preview.Tree_ID} · Segmentation · 信心度{" "}
                  {formatConfidence(preview.YOLO_confidence)}
                </h3>
                {maskUrl ? (
                  <ZoomImage
                    src={maskUrl}
                    title="Segmentation"
                    alt={`${preview.Tree_ID} segmentation`}
                    onOpen={() =>
                      setLightbox({
                        src: maskUrl,
                        title: `${preview.Tree_ID} · Segmentation`,
                      })
                    }
                  />
                ) : (
                  <div className="path-db-empty">尚無 Segmentation 圖</div>
                )}
                <h3>橫切面</h3>
                {sliceUrl ? (
                  <ZoomImage
                    src={sliceUrl}
                    title="橫切面"
                    alt={`${preview.Tree_ID} 橫切面`}
                    onOpen={() =>
                      setLightbox({
                        src: sliceUrl,
                        title: `${preview.Tree_ID} · 橫切面`,
                      })
                    }
                  />
                ) : (
                  <div className="path-db-empty">尚無橫切面圖</div>
                )}
                {photoUrl ? (
                  <>
                    <h3>原圖</h3>
                    <ZoomImage
                      src={photoUrl}
                      title="原圖"
                      alt={`${preview.Tree_ID} 照片`}
                      onOpen={() =>
                        setLightbox({
                          src: photoUrl,
                          title: `${preview.Tree_ID} · 原圖`,
                        })
                      }
                    />
                  </>
                ) : null}
                <h3>點雲側視</h3>
                {cloudPreviewUrl ? (
                  <ZoomImage
                    src={cloudPreviewUrl}
                    title="點雲側視"
                    alt={`${preview.Tree_ID} 點雲側視`}
                    onOpen={() =>
                      setLightbox({
                        src: cloudPreviewUrl,
                        title: `${preview.Tree_ID} · 點雲側視`,
                      })
                    }
                  />
                ) : (
                  <div className="path-db-empty">尚無點雲側視</div>
                )}
              </>
            ) : tab === "measure" ? (
              <div className="measure-panel">
                <div className={`dbh-hero is-${light}`}>
                  <span>{preview.Tree_ID}</span>
                  <strong>
                    {formatDbh(preview.DBH_cm)}
                    <em> 胸徑</em>
                  </strong>
                </div>
                {light === "red" ? (
                  <p className="red-banner">{reviewReason(preview)}</p>
                ) : null}
                <dl className="spec-list">
                  <div>
                    <dt>量測方法</dt>
                    <dd>{methodLabel(preview.DBH_method)}</dd>
                  </div>
                  <div>
                    <dt>弧度覆蓋</dt>
                    <dd>{formatArc(preview.arc_coverage_deg)}</dd>
                  </div>
                  <div className={`is-breast ${preview.dbh_is_strict_breast_height ? "is-ok" : ""}`}>
                    <dt>胸高</dt>
                    <dd>{breastHeightLabel(preview.dbh_is_strict_breast_height)}</dd>
                  </div>
                  <div>
                    <dt>偵測次數</dt>
                    <dd>{preview.num_detections ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>相對座標</dt>
                    <dd className="mono">{formatXyz(preview.Local_XYZ_m)}</dd>
                  </div>
                </dl>
                <label className="field-measure">
                  <span className="field-label">
                    現場手測胸徑
                    <em>不覆蓋演算法數字</em>
                  </span>
                  <input
                    inputMode="decimal"
                    value={field?.dbhCm ?? ""}
                    placeholder="cm"
                    onChange={(event) =>
                      update(preview.Tree_ID, { dbhCm: event.target.value })
                    }
                  />
                </label>
                <label className="field-measure">
                  <span className="field-label">備註</span>
                  <input
                    value={field?.note ?? ""}
                    placeholder="現場補充、樹況、特殊狀況…"
                    onChange={(event) =>
                      update(preview.Tree_ID, { note: event.target.value })
                    }
                  />
                </label>
                {carbon ? (
                  <div className="carbon-box">
                    <h3>碳量估算</h3>
                    <p className="carbon-formula">
                      D = A² × B × C　·　CO₂ = D × 3.667
                    </p>
                    <dl className="spec-list is-carbon">
                      <div>
                        <dt>胸徑換算圓周 A</dt>
                        <dd>
                          {carbon.circumferenceM != null
                            ? `${carbon.circumferenceM.toFixed(3)} m`
                            : "—"}
                        </dd>
                      </div>
                      <div>
                        <dt>樹含碳量 D</dt>
                        <dd>
                          {carbon.carbonD != null
                            ? carbon.carbonD.toFixed(4)
                            : "—"}
                        </dd>
                      </div>
                      <div>
                        <dt>估算 CO₂ 當量</dt>
                        <dd>
                          {carbon.co2Ton != null
                            ? `${carbon.co2Ton.toFixed(3)} ton`
                            : "—"}
                        </dd>
                      </div>
                    </dl>
                    <label className="field-measure">
                      <span className="field-label">
                        樹高 B
                        <em>
                          {carbon.heightEstimated && carbon.heightErrorM != null
                            ? `空白則胸徑粗估，誤差約 ±${carbon.heightErrorM.toFixed(0)} m`
                            : "公尺"}
                        </em>
                      </span>
                      <input
                        inputMode="decimal"
                        value={field?.heightM ?? ""}
                        placeholder={
                          carbon.heightM != null
                            ? `${carbon.heightM.toFixed(1)}（估）`
                            : "m"
                        }
                        onChange={(event) =>
                          update(preview.Tree_ID, {
                            heightM: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label className="field-measure">
                      <span className="field-label">係數 C</span>
                      <select
                        value={coeffSelectValue(field?.coeff)}
                        onChange={(event) => {
                          const value = event.target.value;
                          update(preview.Tree_ID, {
                            coeff:
                              value === "custom"
                                ? isCustomCoeff(field?.coeff)
                                  ? field?.coeff ?? ""
                                  : "0.016"
                                : value,
                          });
                        }}
                      >
                        {CARBON_COEFFS.map((item) => (
                          <option key={item.id} value={String(item.value)}>
                            {item.label}
                          </option>
                        ))}
                        <option value="custom">自訂</option>
                      </select>
                    </label>
                    {isCustomCoeff(field?.coeff) ? (
                      <label className="field-measure">
                        <span className="field-label">自訂係數</span>
                        <input
                          inputMode="decimal"
                          value={field?.coeff ?? ""}
                          placeholder="0.0159"
                          onChange={(event) =>
                            update(preview.Tree_ID, {
                              coeff: event.target.value,
                            })
                          }
                        />
                      </label>
                    ) : null}
                    <label className="field-measure">
                      <span className="field-label">測量日期</span>
                      <input
                        type="date"
                        value={field?.measuredAt ?? ""}
                        placeholder={carbon.measuredAt}
                        onChange={(event) =>
                          update(preview.Tree_ID, {
                            measuredAt: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label><input type="checkbox" checked={field?.strict13m === true}
                      onChange={(event) => update(preview.Tree_ID, { strict13m: event.target.checked })} />
                      確認人工胸徑量於標準 1.3 m（未確認不納入誤差指標）</label>
                  </div>
                ) : null}
              </div>
            ) : hasModel ? (
              <PlyViewer url={modelUrl} label="單木點雲" />
            ) : (
              <div className="path-db-empty">此樹沒有單木點雲</div>
            )}
          </aside>
        </div>
      </div>

      {showFormula ? <FormulaPopup onClose={() => setShowFormula(false)} /> : null}

      {showAssistant ? (
        <InventoryAssistant
          parkName={parkName}
          pathName={pathName}
          report={report}
          measures={measures}
          onClose={() => setShowAssistant(false)}
        />
      ) : null}

      {growthTree && growthTemporal ? (
        <GrowthTrendPopup
          treeId={growthTree.Tree_ID}
          scanCreatedAt={report.created_at}
          temporal={growthTemporal}
          onClose={() => setGrowthTreeId(null)}
        />
      ) : null}

      {lightbox ? (
        <div
          className="path-lightbox"
          role="dialog"
          aria-modal="true"
          aria-label={lightbox.title}
          onClick={(event) => {
            event.stopPropagation();
            setLightbox(null);
          }}
        >
          <div
            className="path-lightbox-card"
            onClick={(event) => event.stopPropagation()}
          >
            <header>
              <strong>{lightbox.title}</strong>
              <button
                type="button"
                className="ghost-btn"
                onClick={() => setLightbox(null)}
              >
                關閉
              </button>
            </header>
            <img src={lightbox.src} alt={lightbox.title} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
