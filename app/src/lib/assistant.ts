import type { FieldMeasure } from "../hooks/useFieldMeasures";
import type { ParkInventoryReport } from "../types";
import { carbonForTree, totalCo2Ton } from "./carbon";
import { inventoryStats, reviewReason, trafficLight } from "./status";

export type AssistantContext = {
  datasetKind?: 'observed' | 'simulated';
  parkName: string;
  pathName: string;
  scanId: string;
  createdAt: string;
  summary: {
    total: number;
    reliable: number;
    pending: number;
    review: number;
    co2Ton: number;
  };
  trees: Array<{
    id: string;
    dbhCm: number | null;
    heightM: number | null;
    co2Ton: number | null;
    status: "green" | "yellow" | "red";
    reviewReason: string;
    confidence: number | null;
    manualDbhCm: number | null;
  }>;
};

export type AssistantReply = {
  verifiedSteps?: string[];
  answer: string;
  evidence: string[];
  provider: "local" | "azure" | "copilot" | "phi4";
  model?: string;
  ragSources?: string[];
  ragQuestionCount?: number;
};

function positive(value: string | undefined) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function inventoryAssistantContext(
  parkName: string,
  pathName: string,
  report: ParkInventoryReport,
  measures: Record<string, FieldMeasure>,
): AssistantContext {
  const stats = inventoryStats(report.trees);
  return {
    datasetKind:report.dataset_kind==='simulated'?'simulated':'observed',
    parkName,
    pathName,
    scanId: report.scan_id,
    createdAt: report.created_at,
    summary: {
      total: stats.total,
      reliable: stats.green,
      pending: stats.yellow,
      review: stats.red,
      co2Ton: totalCo2Ton(report.trees, measures, report.created_at),
    },
    trees: report.trees.map((tree) => {
      const carbon = carbonForTree(
        tree,
        measures[tree.Tree_ID],
        report.created_at,
      );
      return {
        id: tree.Tree_ID,
        dbhCm: tree.DBH_cm,
        heightM: carbon.heightM,
        co2Ton: carbon.co2Ton,
        status: trafficLight(tree),
        reviewReason: reviewReason(tree),
        confidence: tree.YOLO_confidence,
        manualDbhCm: report.dataset_kind !== 'simulated' && measures[tree.Tree_ID]?.strict13m === true && tree.dbh_is_strict_breast_height === true &&
          measures[tree.Tree_ID]?.measuredAt === report.created_at.slice(0,10)
          ? positive(measures[tree.Tree_ID]?.dbhCm) : null,
      };
    }),
  };
}

export async function askInventoryAssistant(
  question: string,
  context: AssistantContext,
): Promise<AssistantReply> {
  const response = await fetch("/api/assistant", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, context }),
  });
  const body = (await response.json()) as AssistantReply & { error?: string };
  if (!response.ok) throw new Error(body.error || "AI 助理暫時無法回答");
  return body;
}

export type AssistantStatus = {
  requireProvider?: boolean;
  provider: string;
  billableAllowed: boolean;
  copilotConfigured: boolean;
  azureConfigured: boolean;
  phi4Configured: boolean;
  phi4CloudConfigured: boolean;
  activeMode: "local" | "copilot" | "azure" | "phi4" | "phi4-cloud" | string;
  hints: string[];
  connection?: { state: string; models: string[] } | null;
  lastInference?: { provider: string; model?: string; verifiedAt: string } | null;
};

export async function fetchAssistantStatus(): Promise<AssistantStatus> {
  const response = await fetch("/api/assistant/status", {
    credentials: "same-origin",
    signal: AbortSignal.timeout(12000),
  });
  if (!response.ok) {
    return {
      provider: "local",
      billableAllowed: false,
      copilotConfigured: false,
      azureConfigured: false,
      phi4Configured: false,
      phi4CloudConfigured: false,
      activeMode: "unavailable",
      hints: ["無法讀取助理狀態，請確認服務與登入狀態。"],
    };
  }
  return (await response.json()) as AssistantStatus;
}
