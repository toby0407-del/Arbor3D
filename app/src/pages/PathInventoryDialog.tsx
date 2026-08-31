import { useEffect, useMemo, useRef, useState } from "react";
import { PathTreeMap } from "../components/PathTreeMap";
import { PlyViewer } from "../components/PlyViewer";
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
import {
  formatScanMonthDay,
  growthStatusLabel,
  temporalGrowth,
  type GrowthPoint,
  type GrowthStatus,
  type TemporalGrowth,
} from "../lib/growth";
import { downloadInventoryCsv } from "../lib/csv";
import {
  formatArc,
  formatConfidence,
  formatDbh,
  formatScanTime,
  formatXyz,
  methodLabel,
} from "../lib/format";
import { scanAssetUrl } from "../lib/scanMedia";
import {
  inventoryStats,
  isReviewTree,
  reviewReason,
  trafficLight,
} from "../lib/status";
import type { ParkInventoryReport, TrafficLight, TreeRecord } from "../types";

type PreviewTab = "images" | "measure" | "model";
type Filter = "all" | TrafficLight | "review" | "warning";
function FormulaPopup({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="formula-popup-backdrop"
      onClick={(event) => {
        event.stopPropagation();
        onClose();
      }}
    >
      <div
        className="formula-popup"
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <strong>碳吸收公式</strong>
          <button type="button" className="ghost-btn" onClick={onClose}>
            ✕
          </button>
        </header>
        <table className="formula-table">
          <tbody>
            <tr>
              <td><strong>A</strong></td>
              <td>1.3 m 圓周</td>
              <td><code>π × DBH</code></td>
            </tr>
            <tr>
              <td><strong>B</strong></td>
              <td>樹高</td>
              <td><code>1.3 + 1.8√DBH</code></td>
            </tr>
            <tr>
              <td><strong>C</strong></td>
              <td>係數</td>
              <td><code>0.0159</code></td>
            </tr>
            <tr>
              <td><strong>D</strong></td>
              <td>含碳</td>
              <td><code>A² × B × C</code></td>
            </tr>
            <tr>
              <td><strong>CO₂</strong></td>
              <td>當量 t</td>
              <td><code>D × 3.667</code></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

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
      {status === "abnormal" ? (
        <span className="growth-warn-tag">Warning</span>
      ) : null}
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
  const chartW = 420;
  const chartH = 150;
  const pad = { l: 36, r: 10, t: 12, b: 26 };
  const values = points.map((point) => point.dbhCm);
  const min = Math.min(...values) - 0.6;
  const max = Math.max(...values) + 0.6;
  const span = Math.max(0.8, max - min);
  const xy = (point: GrowthPoint, index: number) => {
    const x =
      pad.l + (index / Math.max(1, points.length - 1)) * (chartW - pad.l - pad.r);
    const y = pad.t + (1 - (point.dbhCm - min) / span) * (chartH - pad.t - pad.b);
    return { x, y };
  };
  const coords = points.map(xy);
  const line = coords
    .map((pt, index) => `${index === 0 ? "M" : "L"}${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`)
    .join(" ");
  const fitClass =
    status === "abnormal" ? "off" : status === "normal" ? "ok" : "watch";

  return (
    <div
      className="formula-popup-backdrop"
      onClick={(event) => {
        event.stopPropagation();
        onClose();
      }}
    >
      <div
        className="formula-popup is-growth"
        role="dialog"
        aria-modal="true"
        aria-labelledby="growth-pop-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header>
          <strong id="growth-pop-title">時序成長</strong>
          <button type="button" className="ghost-btn" onClick={onClose}>
            關閉
          </button>
        </header>
        <div className="growth-banner">
          {treeId}　{formatScanMonthDay(scanCreatedAt)}　{current.dbhCm.toFixed(1)} cm
        </div>
        <ol className="temporal-pipe">
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
              <li key={snap.role} className={`is-${snap.role}`}>
                <span>{snap.roleLabel}</span>
                <strong>
                  {snap.periodLabel}　{snap.dbhCm.toFixed(2)} cm
                </strong>
                <em>{deltaText}</em>
              </li>
            );
          })}
        </ol>
        <p className={`growth-fit-stamp is-${fitClass}`}>
          <TreeGlyph />
          {growthStatusLabel(status)}
        </p>
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
                  stroke="#d7d2c6"
                />
                <text x={4} y={y + 3.5} className="growth-axis">
                  {label.toFixed(1)}
                </text>
              </g>
            );
          })}
          <path d={line} fill="none" stroke="#000095" strokeWidth="2.1" />
          {coords.map((pt, index) => {
            const point = points[index];
            const measured = point.kind === "measured";
            return (
              <g key={`${point.year}-${point.month}-${point.label}`}>
                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r={measured ? 5 : 3.4}
                  fill={measured ? "#c40000" : "#2f6b3a"}
                  stroke="#fff8e8"
                  strokeWidth="1"
                />
                <text x={pt.x} y={chartH - 8} textAnchor="middle" className="growth-axis">
                  {snaps[index].roleLabel}
                </text>
              </g>
            );
          })}
        </svg>
        <p className="formula-note">{temporal.carbonNote}</p>
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
    return <div className="path-db-empty">無圖</div>;
  }
  return (
    <button type="button" className="path-db-thumb" onClick={onOpen}>
      <img src={src} alt={alt} onError={() => setOk(false)} />
    </button>
  );
}

function temporalForTree(
  tree: TreeRecord,
  field: { dbhCm?: string } | undefined,
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
    scanIso,
    note: tree.DBH_note,
    yoloConfidence: tree.YOLO_confidence,
  });
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
  const [growthTreeId, setGrowthTreeId] = useState<string | null>(null);
  const [tab, setTab] = useState<PreviewTab>("images");
  const [filter, setFilter] = useState<Filter>("all");
  const { measures, update } = useFieldMeasures(report.scan_id);
  const stats = useMemo(() => inventoryStats(report.trees), [report.trees]);
  const co2Total = useMemo(
    () => totalCo2Ton(report.trees, measures, report.created_at),
    [measures, report.created_at, report.trees],
  );
  const growthById = useMemo(() => {
    const map = new Map<string, TemporalGrowth>();
    for (const tree of report.trees) {
      const carbon = carbonForTree(tree, measures[tree.Tree_ID], report.created_at);
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
  const growthCounts = useMemo(() => {
    let normal = 0;
    let stalled = 0;
    let watch = 0;
    let abnormal = 0;
    for (const temporal of growthById.values()) {
      if (temporal.status === "normal") normal += 1;
      else if (temporal.status === "stalled") stalled += 1;
      else if (temporal.status === "watch") watch += 1;
      else abnormal += 1;
    }
    return { normal, stalled, watch, abnormal };
  }, [growthById]);
  const warningTrees = useMemo(
    () => report.trees.filter((tree) => growthById.get(tree.Tree_ID)?.warning),
    [growthById, report.trees],
  );
  const visible = useMemo(() => {
    return report.trees.filter((tree) => {
      if (filter === "all") return true;
      if (filter === "review") return isReviewTree(tree);
      if (filter === "warning") return growthById.get(tree.Tree_ID)?.warning === true;
      return trafficLight(tree.DBH_note) === filter;
    });
  }, [filter, growthById, report.trees]);

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
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (lightbox) {
          setLightbox(null);
          return;
        }
        if (growthTreeId) {
          setGrowthTreeId(null);
          return;
        }
        if (showFormula) {
          setShowFormula(false);
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
  }, [growthTreeId, lightbox, onClose, onPreviewTree, preview, showFormula, visible]);

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
  const modelUrl = preview
    ? scanAssetUrl(
        report.scan_id,
        preview.Single_Tree_Ply || preview["3D_Model_Path"],
      )
    : null;
  const field = preview ? measures[preview.Tree_ID] : undefined;
  const light = preview ? trafficLight(preview.DBH_note) : "red";
  const carbon = preview
    ? carbonForTree(preview, field, report.created_at)
    : null;
  const growthTree =
    report.trees.find((tree) => tree.Tree_ID === growthTreeId) ?? null;

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
              {growthCounts.abnormal > 0 ? (
                <span className="pill is-red">Warning {growthCounts.abnormal}</span>
              ) : null}
              <span className="pill is-green">
                CO₂ {co2Total.toFixed(2)} t
              </span>
            </div>
          </div>
          <div className="path-db-head-actions">
            <button
              type="button"
              className="formula-btn"
              title="碳吸收公式說明"
              aria-label="碳吸收公式說明"
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
            <PathTreeMap
              trees={report.trees}
              selectedId={preview?.Tree_ID ?? null}
              onPick={onPreviewTree}
            />
            {warningTrees.length > 0 ? (
              <section className="review-mini is-warning">
                <h3>Warning</h3>
                <ul>
                  {warningTrees.map((tree) => (
                    <li key={tree.Tree_ID}>
                      <button
                        type="button"
                        className="text-btn"
                        onClick={() => {
                          setFilter("warning");
                          onPreviewTree(tree.Tree_ID);
                        }}
                      >
                        {tree.Tree_ID}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
          </aside>

          <div className="path-db-table-wrap is-scroll-x">
            <div className="inv-filters" role="tablist" aria-label="篩選">
              {(
                [
                  ["all", `全 ${stats.total}`, true],
                  ["green", `綠 ${stats.green}`, stats.green > 0 && stats.green < stats.total],
                  ["yellow", `黃 ${stats.yellow}`, stats.yellow > 0],
                  ["red", `紅 ${stats.red}`, stats.red > 0],
                  ["warning", `! ${growthCounts.abnormal}`, growthCounts.abnormal > 0],
                ] as const
              )
                .filter(([, , show]) => show)
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
              <div className="path-db-empty">無資料</div>
            ) : (
              <table className="compact-tree-table">
                <colgroup>
                  <col className="col-id" />
                  <col className="col-dbh" />
                  <col className="col-h" />
                  <col className="col-co2" />
                  <col className="col-growth" />
                </colgroup>
                <thead>
                  <tr>
                    <th>樹號</th>
                    <th>胸徑</th>
                    <th>樹高</th>
                    <th>CO₂</th>
                    <th className="growth-col">健康度</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((tree) => {
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
                        className={active ? "is-active" : undefined}
                        onClick={() => onPreviewTree(tree.Tree_ID)}
                      >
                        <td>{tree.Tree_ID.replace("Tree_", "#")}</td>
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
                        {visible
                          .reduce((sum, tree) => {
                            const r = carbonForTree(
                              tree,
                              measures[tree.Tree_ID],
                              report.created_at,
                            );
                            return sum + (r.co2Ton ?? 0);
                          }, 0)
                          .toFixed(3)}{" "}
                        t
                      </strong>
                    </td>
                    <td></td>
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
              ).map(([id, label]) => (
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
              <div className="path-db-empty">無資料</div>
            ) : tab === "images" ? (
              <>
                <h3>
                  {preview.Tree_ID}　{formatConfidence(preview.YOLO_confidence)}
                </h3>
                {maskUrl ? (
                  <ZoomImage
                    src={maskUrl}
                    title="Segmentation"
                    alt={`${preview.Tree_ID} segmentation`}
                    onOpen={() =>
                      setLightbox({
                        src: maskUrl,
                        title: `${preview.Tree_ID}`,
                      })
                    }
                  />
                ) : (
                  <div className="path-db-empty">無圖</div>
                )}
                {sliceUrl ? (
                  <ZoomImage
                    src={sliceUrl}
                    title="橫切面"
                    alt={`${preview.Tree_ID} 橫切面`}
                    onOpen={() =>
                      setLightbox({
                        src: sliceUrl,
                        title: `${preview.Tree_ID}`,
                      })
                    }
                  />
                ) : (
                  <div className="path-db-empty">無圖</div>
                )}
                {photoUrl ? (
                  <ZoomImage
                    src={photoUrl}
                    title="原圖"
                    alt={`${preview.Tree_ID} 照片`}
                    onOpen={() =>
                      setLightbox({
                        src: photoUrl,
                        title: `${preview.Tree_ID}`,
                      })
                    }
                  />
                ) : null}
                {cloudPreviewUrl ? (
                  <ZoomImage
                    src={cloudPreviewUrl}
                    title="點雲"
                    alt={`${preview.Tree_ID} 點雲`}
                    onOpen={() =>
                      setLightbox({
                        src: cloudPreviewUrl,
                        title: `${preview.Tree_ID}`,
                      })
                    }
                  />
                ) : (
                  <div className="path-db-empty">無圖</div>
                )}
              </>
            ) : tab === "measure" ? (
              <div className="measure-panel">
                <div className={`dbh-hero is-${light}`}>
                  <span>{preview.Tree_ID}</span>
                  <strong>
                    {formatDbh(preview.DBH_cm)}
                  </strong>
                </div>
                {light === "red" ? (
                  <p className="red-banner">{reviewReason(preview)}</p>
                ) : null}
                <dl className="spec-list">
                  <div>
                    <dt>方法</dt>
                    <dd>{methodLabel(preview.DBH_method)}</dd>
                  </div>
                  <div>
                    <dt>弧度</dt>
                    <dd>{formatArc(preview.arc_coverage_deg)}</dd>
                  </div>
                  <div>
                    <dt>次數</dt>
                    <dd>{preview.num_detections ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>XYZ</dt>
                    <dd className="mono">{formatXyz(preview.Local_XYZ_m)}</dd>
                  </div>
                </dl>
                <label className="field-measure">
                  <span className="field-label">手測</span>
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
                    placeholder="備註"
                    onChange={(event) =>
                      update(preview.Tree_ID, { note: event.target.value })
                    }
                  />
                </label>
                {carbon ? (
                  <div className="carbon-box">
                    <h3>碳</h3>
                    <dl className="spec-list is-carbon">
                      <div>
                        <dt>A 圓周</dt>
                        <dd>
                          {carbon.circumferenceM != null
                            ? `${carbon.circumferenceM.toFixed(3)} m`
                            : "—"}
                        </dd>
                      </div>
                    </dl>
                    <label className="field-measure">
                      <span className="field-label">B 樹高</span>
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
                      <span className="field-label">C 係數</span>
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
                    <dl className="spec-list is-carbon">
                      <div>
                        <dt>D 含碳量</dt>
                        <dd>
                          {carbon.carbonD != null
                            ? carbon.carbonD.toFixed(4)
                            : "—"}
                        </dd>
                      </div>
                      <div>
                        <dt>CO₂</dt>
                        <dd>
                          {carbon.co2Ton != null
                            ? `${carbon.co2Ton.toFixed(3)} ton`
                            : "—"}
                        </dd>
                      </div>
                    </dl>
                    <label className="field-measure">
                      <span className="field-label">日期</span>
                      <input
                        value={field?.measuredAt ?? ""}
                        placeholder={carbon.measuredAt}
                        onChange={(event) =>
                          update(preview.Tree_ID, {
                            measuredAt: event.target.value,
                          })
                        }
                      />
                    </label>
                  </div>
                ) : null}
              </div>
            ) : (
              <PlyViewer
                url={modelUrl}
                label={preview.Single_Tree_Ply ? "單木點雲" : "高斯濺射"}
              />
            )}
          </aside>
        </div>
      </div>

      {showFormula ? <FormulaPopup onClose={() => setShowFormula(false)} /> : null}

      {growthTree && growthById.get(growthTree.Tree_ID) ? (
        <GrowthTrendPopup
          treeId={growthTree.Tree_ID}
          scanCreatedAt={report.created_at}
          temporal={growthById.get(growthTree.Tree_ID)!}
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
