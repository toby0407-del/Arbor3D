import type { FieldMeasure } from "../hooks/useFieldMeasures";
import type { ParkInventoryReport } from "../types";
import { carbonForTree, totalCo2Ton } from "./carbon";
import { inventoryStats, reviewReason, trafficLight } from "./status";

export type AssistantContext = {
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
  answer: string;
  evidence: string[];
  provider: "local" | "azure";
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
    parkName,
    pathName,
    scanId: report.scan_id,
    createdAt: report.created_at,
    summary: {
      total: stats.total,
      reliable: stats.green,
      pending: stats.yellow,
      review: stats.review,
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
        manualDbhCm: positive(measures[tree.Tree_ID]?.dbhCm),
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
