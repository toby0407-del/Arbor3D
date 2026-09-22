import {
  DEFAULT_CARBON_COEFF,
  circumferenceMFromDbhCm,
  co2EquivalentTon,
  estimateHeightM,
  treeCarbonD,
} from "./carbon";
import type { QuarterlyObservation } from "../types";

/** Stored quarterly scenarios, never relabelled as field observations. */
export function quarterlyGrowth(rows: QuarterlyObservation[]): TemporalGrowth {
  const points: GrowthPoint[] = rows.map(row => {
    const [year, month, day] = row.date.split('-').map(Number);
    return { year, month, day, label: row.quarter, dbhCm: row.simulated_ai_dbh_cm,
      heightM: row.simulated_height_m, kind: 'backcast', source: 'sim' };
  });
  const current = toSnap('current', '末期模擬', points.at(-1)!);
  const previous = toSnap('previous', '前季模擬', points.at(-2) ?? points[0]);
  const trend = toSnap('trend', '起始模擬', points[0]);
  const delta = current.dbhCm - previous.dbhCm;
  const status: GrowthStatus = delta < -0.5 ? 'abnormal' : Math.abs(delta) < 0.1 ? 'stalled' : 'normal';
  return { previous, current, trend, points, status, fit: growthFitFromStatus(status),
    warning: status === 'abnormal', expectedIncrementCm: 0,
    periodIncrementCm: delta, carbonDeltaTon: current.co2Ton - previous.co2Ton,
    carbonNote: '季度情境比較；數值與狀態均為模擬，非健康診斷。' };
}

/** 本年度固定拍攝期：3 月、7 月、9 月。 */
export const SURVEY_MONTHS = [3, 7, 9] as const;

/** 都市行道樹年胸徑增量粗估（cm／年）。幼木較快、大木較慢。 */
export function annualDbhIncrementCm(dbhCm: number): number {
  const d = Math.max(1, dbhCm);
  return Math.max(0.32, Math.min(1.28, 1.18 * Math.exp(-0.015 * d)));
}

export type GrowthKind = "backcast" | "measured" | "forecast";
/** measured = 人工量測；ai = 掃描演算法；sim = 模擬／推估 */
export type GrowthSource = "measured" | "ai" | "sim";
export type GrowthFit = "ok" | "watch" | "off";
export type GrowthStatus = "normal" | "stalled" | "watch" | "abnormal";
export type TemporalRole = "previous" | "current" | "trend";
export type GrowthRangeMode = "year" | "quarter" | "custom";

export type GrowthPoint = {
  year: number;
  month: number;
  day: number;
  label: string;
  dbhCm: number;
  heightM: number;
  kind: GrowthKind;
  source: GrowthSource;
};

export type TemporalSnap = {
  role: TemporalRole;
  roleLabel: string;
  periodLabel: string;
  dbhCm: number;
  heightM: number;
  kind: GrowthKind;
  source: GrowthSource;
  co2Ton: number;
};

export type TemporalGrowth = {
  previous: TemporalSnap;
  current: TemporalSnap;
  trend: TemporalSnap;
  /** 完整月序列（含大量模擬點） */
  points: GrowthPoint[];
  status: GrowthStatus;
  fit: GrowthFit;
  warning: boolean;
  expectedIncrementCm: number;
  periodIncrementCm: number;
  carbonDeltaTon: number;
  carbonNote: string;
};

export type GrowthMonth = { year: number; month: number };

export type GrowthRange = {
  mode: GrowthRangeMode;
  from: GrowthMonth;
  to: GrowthMonth;
};

const MS_PER_YEAR = 365.25 * 24 * 60 * 60 * 1000;
/** 往前灌幾年、往後灌幾年的月序列（模擬為主；每年都灌滿 1–12 月） */
const SERIES_YEARS_BACK = 3;
const SERIES_YEARS_FORWARD = 2;

export function parseScanDate(iso: string): Date {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? new Date() : date;
}

function midMonth(year: number, month: number): Date {
  return new Date(year, month - 1, 15);
}

function clampMonth(year: number, month: number): GrowthMonth {
  let y = year;
  let m = month;
  while (m < 1) {
    m += 12;
    y -= 1;
  }
  while (m > 12) {
    m -= 12;
    y += 1;
  }
  return { year: y, month: m };
}

function monthIndex(m: GrowthMonth): number {
  return m.year * 12 + (m.month - 1);
}

function addMonths(m: GrowthMonth, delta: number): GrowthMonth {
  return clampMonth(m.year, m.month + delta);
}

function heightAtDbh(
  dbhCm: number,
  measuredHeightM: number | null,
  baseDbhCm: number,
): number {
  if (measuredHeightM != null && baseDbhCm > 0) {
    return Math.max(2.5, measuredHeightM * (dbhCm / baseDbhCm));
  }
  return estimateHeightM(dbhCm);
}

function co2At(dbhCm: number, heightM: number): number {
  return co2EquivalentTon(
    treeCarbonD(circumferenceMFromDbhCm(dbhCm), heightM, DEFAULT_CARBON_COEFF),
  );
}

function kindForSurvey(scan: Date, survey: Date): GrowthKind {
  return survey.getTime() < scan.getTime() ? "backcast" : "forecast";
}

/** 穩定雜訊，同一棵樹同一月份結果固定 */
function simNoise(seed: number, year: number, month: number): number {
  const x = Math.sin(seed * 12.9898 + year * 78.233 + month * 4.141) * 43758.5453;
  return (x - Math.floor(x)) * 2 - 1;
}

function previousSurveyDate(scan: Date): Date {
  const year = scan.getFullYear();
  const earlier = SURVEY_MONTHS.map((month) => midMonth(year, month)).filter(
    (date) => date.getTime() < scan.getTime(),
  );
  return earlier.at(-1) ?? midMonth(year - 1, SURVEY_MONTHS[SURVEY_MONTHS.length - 1]);
}

function nextSurveyDate(scan: Date): Date {
  const year = scan.getFullYear();
  const later = SURVEY_MONTHS.map((month) => midMonth(year, month)).find(
    (date) => date.getTime() > scan.getTime(),
  );
  return later ?? midMonth(year + 1, SURVEY_MONTHS[0]);
}

function toSnap(
  role: TemporalRole,
  roleLabel: string,
  point: GrowthPoint,
): TemporalSnap {
  return {
    role,
    roleLabel,
    periodLabel: `${point.year}年${point.month}月`,
    dbhCm: point.dbhCm,
    heightM: point.heightM,
    kind: point.kind,
    source: point.source,
    co2Ton: co2At(point.dbhCm, point.heightM),
  };
}

export function classifyGrowth(opts: {
  dbhCm: number | null | undefined;
  note?: string | null;
  yoloConfidence?: number | null;
}): GrowthStatus {
  const dbh = opts.dbhCm;
  if (dbh == null || !(dbh > 0)) return "abnormal";
  const note = opts.note ?? "";
  if (
    note === "no_measurement" ||
    note.includes("wide_caliper") ||
    note.includes("gap")
  ) {
    return "abnormal";
  }
  if (dbh >= 110) return "abnormal";
  if (dbh >= 90 || annualDbhIncrementCm(dbh) <= 0.38) return "stalled";
  if (dbh < 14 || (opts.yoloConfidence != null && opts.yoloConfidence < 0.42)) {
    return "watch";
  }
  return "normal";
}

export function growthFitFromStatus(status: GrowthStatus): GrowthFit {
  if (status === "abnormal") return "off";
  if (status === "normal") return "ok";
  return "watch";
}

export function growthStatusLabel(status: GrowthStatus): string {
  if (status === "normal") return "正常";
  if (status === "stalled") return "停長";
  if (status === "watch") return "觀察";
  return "異常";
}

function carbonNoteFor(
  status: GrowthStatus,
  carbonDeltaTon: number,
  increment: number,
): string {
  const delta =
    carbonDeltaTon >= 0
      ? `+${carbonDeltaTon.toFixed(3)} t`
      : `−${Math.abs(carbonDeltaTon).toFixed(3)} t`;
  if (status === "abnormal") return `碳匯 ${delta}（不計）`;
  if (status === "stalled") return `${increment.toFixed(2)} cm／年　${delta}`;
  if (status === "watch") return `碳匯 ${delta}（參考）`;
  return `碳匯 ${delta}`;
}

function pointFromDate(
  date: Date,
  scan: Date,
  baseDbh: number,
  measuredHeight: number | null,
  increment: number,
  seed: number,
  forceReal: boolean,
  baseSource: GrowthSource = "ai",
): GrowthPoint {
  const yearsDelta = (date.getTime() - scan.getTime()) / MS_PER_YEAR;
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const kind = forceReal ? "measured" : kindForSurvey(scan, date);
  const source: GrowthSource = forceReal ? baseSource : "sim";
  const noise =
    source === "sim"
      ? simNoise(seed, year, month) * Math.min(0.35, increment * 0.22)
      : 0;
  const dbh = Math.max(3, baseDbh + increment * yearsDelta + noise);
  return {
    year,
    month,
    day,
    label: `${year}/${month}`,
    dbhCm: dbh,
    heightM: heightAtDbh(dbh, measuredHeight, baseDbh),
    kind,
    source,
  };
}

/** 產生多年月序列：僅掃描當下保留量測或 AI 來源，其餘為模擬；每年都含 1–12 月 */
function buildSeries(opts: {
  scan: Date;
  baseDbh: number;
  measuredHeight: number | null;
  increment: number;
  seed: number;
  baseSource: GrowthSource;
}): GrowthPoint[] {
  const { scan, baseDbh, measuredHeight, increment, seed } = opts;
  const start: GrowthMonth = {
    year: scan.getFullYear() - SERIES_YEARS_BACK,
    month: 1,
  };
  // 明確灌到「掃描年 + FORWARD」的 12 月，避免只到年中（例如 2027/7）
  const end: GrowthMonth = {
    year: scan.getFullYear() + SERIES_YEARS_FORWARD,
    month: 12,
  };
  const scanMonth = { year: scan.getFullYear(), month: scan.getMonth() + 1 };
  const points: GrowthPoint[] = [];

  for (
    let cursor: GrowthMonth = start;
    monthIndex(cursor) <= monthIndex(end);
    cursor = addMonths(cursor, 1)
  ) {
    const isScanMonth =
      cursor.year === scanMonth.year && cursor.month === scanMonth.month;
    const date = isScanMonth ? scan : midMonth(cursor.year, cursor.month);
    points.push(
      pointFromDate(
        date,
        scan,
        baseDbh,
        measuredHeight,
        increment,
        seed,
        isScanMonth,
        opts.baseSource,
      ),
    );
  }
  return points;
}

export function quarterOfMonth(month: number): 1 | 2 | 3 | 4 {
  return (Math.floor((month - 1) / 3) + 1) as 1 | 2 | 3 | 4;
}

export function defaultGrowthRange(
  mode: GrowthRangeMode,
  scanIso: string,
): GrowthRange {
  const scan = parseScanDate(scanIso);
  const year = scan.getFullYear();
  const month = scan.getMonth() + 1;
  if (mode === "year") {
    return { mode, from: { year, month: 1 }, to: { year, month: 12 } };
  }
  if (mode === "quarter") {
    const q = quarterOfMonth(month);
    const startMonth = (q - 1) * 3 + 1;
    return {
      mode,
      from: { year, month: startMonth },
      to: { year, month: startMonth + 2 },
    };
  }
  return {
    mode: "custom",
    from: clampMonth(year - 1, month),
    to: { year, month },
  };
}

export function shiftGrowthRange(range: GrowthRange, delta: number): GrowthRange {
  if (range.mode === "year") {
    return {
      ...range,
      from: { year: range.from.year + delta, month: 1 },
      to: { year: range.to.year + delta, month: 12 },
    };
  }
  if (range.mode === "quarter") {
    const shifted = addMonths(range.from, delta * 3);
    const qStart = clampMonth(
      shifted.year,
      (quarterOfMonth(shifted.month) - 1) * 3 + 1,
    );
    return {
      ...range,
      from: qStart,
      to: addMonths(qStart, 2),
    };
  }
  return range;
}

export function filterPointsByRange(
  points: GrowthPoint[],
  range: GrowthRange,
): GrowthPoint[] {
  const a = monthIndex(range.from);
  const b = monthIndex(range.to);
  const lo = Math.min(a, b);
  const hi = Math.max(a, b);
  return points.filter((p) => {
    const i = monthIndex({ year: p.year, month: p.month });
    return i >= lo && i <= hi;
  });
}

export function formatRangeTitle(range: GrowthRange): string {
  if (range.mode === "year") return `${range.from.year}年`;
  if (range.mode === "quarter") {
    return `${range.from.year}年 Q${quarterOfMonth(range.from.month)}`;
  }
  return `${range.from.year}/${range.from.month}–${range.to.year}/${range.to.month}`;
}

export function formatAxisMonthYear(point: GrowthPoint): string {
  return `${point.year}/${point.month}`;
}

export function availableYears(points: GrowthPoint[]): number[] {
  const years = new Set(points.map((p) => p.year));
  return [...years].sort((a, b) => a - b);
}

/** Previous Survey → Current Survey → Growth Trend（另附完整模擬月序列） */
export function temporalGrowth(opts: {
  baseSource?: GrowthSource;
  dbhCm: number;
  heightM: number | null;
  heightEstimated: boolean;
  scanIso: string;
  note?: string | null;
  yoloConfidence?: number | null;
  /** 用於穩定模擬雜訊；不傳則用胸徑種子 */
  seed?: number;
}): TemporalGrowth {
  const scan = parseScanDate(opts.scanIso);
  const baseDbh = Math.max(1, opts.dbhCm);
  const measuredHeight = opts.heightEstimated ? null : opts.heightM;
  const increment = annualDbhIncrementCm(baseDbh);
  const seed = opts.seed ?? Math.round(baseDbh * 1000);
  const prevDate = previousSurveyDate(scan);
  const nextDate = nextSurveyDate(scan);

  const previousPoint = pointFromDate(
    prevDate,
    scan,
    baseDbh,
    measuredHeight,
    increment,
    seed,
    false,
  );
  const currentPoint = pointFromDate(
    scan,
    scan,
    baseDbh,
    measuredHeight,
    increment,
    seed,
    true,
    opts.baseSource ?? "ai",
  );
  const trendPoint = pointFromDate(
    nextDate,
    scan,
    baseDbh,
    measuredHeight,
    increment,
    seed,
    false,
  );

  const previous = toSnap("previous", "前期", previousPoint);
  const current = toSnap("current", "本期", currentPoint);
  const trend = toSnap("trend", "趨勢", trendPoint);
  const status = classifyGrowth({
    dbhCm: opts.dbhCm,
    note: opts.note,
    yoloConfidence: opts.yoloConfidence,
  });
  const carbonDeltaTon = current.co2Ton - previous.co2Ton;
  const series = buildSeries({
    scan,
    baseDbh,
    measuredHeight,
    increment,
    seed,
    baseSource: opts.baseSource ?? "ai",
  });

  return {
    previous,
    current,
    trend,
    points: series,
    status,
    fit: growthFitFromStatus(status),
    warning: status === "abnormal",
    expectedIncrementCm: increment,
    periodIncrementCm: current.dbhCm - previous.dbhCm,
    carbonDeltaTon,
    carbonNote: carbonNoteFor(status, carbonDeltaTon, increment),
  };
}

export function formatScanMonthDay(iso: string): string {
  const date = parseScanDate(iso);
  return `${date.getMonth() + 1}月${date.getDate()}日`;
}
