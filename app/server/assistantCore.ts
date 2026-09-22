export type AssistantTree = {
  id: string;
  dbhCm: number | null;
  heightM: number | null;
  co2Ton: number | null;
  status: "green" | "yellow" | "red";
  reviewReason: string;
  confidence: number | null;
  manualDbhCm: number | null;
};

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
  trees: AssistantTree[];
};

export type AssistantReply = {
  answer: string;
  evidence: string[];
  provider: "local" | "azure";
};

const fmt = (value: number, digits = 2) => value.toFixed(digits);

function listTrees(trees: AssistantTree[]) {
  return trees.slice(0, 8).map((tree) => tree.id).join("、");
}

export function localAssistantReply(
  question: string,
  context: AssistantContext,
): AssistantReply {
  const q = question.toLowerCase();
  const reviewTrees = context.trees.filter((tree) => tree.status !== "green");
  const validDbh = context.trees.filter(
    (tree): tree is AssistantTree & { dbhCm: number } => tree.dbhCm != null,
  );
  const manualPairs = context.trees.filter(
    (tree) => tree.dbhCm != null && tree.manualDbhCm != null,
  );
  const evidence = [
    `掃描 ${context.scanId}，共 ${context.summary.total} 棵`,
    `較可信 ${context.summary.reliable}、待確認 ${context.summary.pending}、需複核 ${context.summary.review}`,
  ];

  if (/複核|異常|紅燈|問題|優先/.test(q)) {
    if (reviewTrees.length === 0) {
      return {
        provider: "local",
        answer: "這批盤點目前沒有被標成待確認或需複核的樹木。仍建議抽樣人工量測，確認模型在這個場域沒有系統性偏差。",
        evidence,
      };
    }
    const reasons = reviewTrees.slice(0, 5).map((tree) =>
      `${tree.id}（${tree.reviewReason || "量測條件待確認"}）`,
    );
    return {
      provider: "local",
      answer: `建議優先複核 ${reviewTrees.length} 棵：${reasons.join("、")}。先做 1.3 m 標準胸高人工量測，再補拍遮擋嚴重或信心偏低的樹幹影像。`,
      evidence: [...evidence, `待處理樹號：${listTrees(reviewTrees)}`],
    };
  }

  if (/碳|co2|co₂|碳匯|排放/.test(q)) {
    return {
      provider: "local",
      answer: `本次盤點估算 CO₂ 當量合計約 ${fmt(context.summary.co2Ton)} ton。這是由胸徑、樹高與係數推估的管理指標；樹高或係數尚未實測時，不應作為正式碳權或查證數字。`,
      evidence: [...evidence, `估算 CO₂ 當量 ${fmt(context.summary.co2Ton)} ton`],
    };
  }

  if (/精度|誤差|人工|mae|準確|可信|信心/.test(q)) {
    if (manualPairs.length === 0) {
      return {
        provider: "local",
        answer: "目前沒有同一棵樹的有效人工胸徑配對，因此還不能宣稱 AI 的 MAE 或準確率。請先填寫人工胸徑、量測日期，並勾選確認是在 1.3 m 標準胸高量測，再匯出分析資料。",
        evidence: [...evidence, "AI／人工有效配對 0 筆"],
      };
    }
    const errors = manualPairs.map((tree) =>
      Math.abs((tree.dbhCm ?? 0) - (tree.manualDbhCm ?? 0)),
    );
    const mae = errors.reduce((sum, value) => sum + value, 0) / errors.length;
    return {
      provider: "local",
      answer: `目前有 ${manualPairs.length} 筆 AI／人工配對，畫面內的初步 MAE 約 ${fmt(mae)} cm。正式競賽指標仍應只納入已確認 1.3 m 胸高且日期完整的資料。`,
      evidence: [...evidence, `初步有效配對 ${manualPairs.length} 筆`, `初步 MAE ${fmt(mae)} cm`],
    };
  }

  if (/最大|最粗|胸徑|dbh/.test(q) && validDbh.length > 0) {
    const largest = [...validDbh].sort((a, b) => b.dbhCm - a.dbhCm)[0];
    return {
      provider: "local",
      answer: `${largest.id} 的 AI 胸徑最大，約 ${fmt(largest.dbhCm)} cm。若它同時被標記為待複核，應先人工確認，避免併株或虛擬卡尺偏寬造成高估。`,
      evidence: [...evidence, `${largest.id}：${fmt(largest.dbhCm)} cm`],
    };
  }

  return {
    provider: "local",
    answer: `這次在「${context.parkName}／${context.pathName}」盤點 ${context.summary.total} 棵樹，其中較可信 ${context.summary.reliable} 棵，待確認 ${context.summary.pending} 棵，需複核 ${context.summary.review} 棵。建議先完成待複核樹木的標準胸高人工量測，再把分析資料送到 Power BI／Fabric 做跨期比較。`,
    evidence,
  };
}

export function assistantSystemPrompt(context: AssistantContext) {
  return [
    "你是 Arbor3D 校園樹木盤點助理。請使用繁體中文，回答精簡、可行動。",
    "只能根據下方 JSON 證據回答；不得捏造樹種、健康診斷、跨期實測、模型精度或碳權結論。",
    "若資料不足，明確說明缺少什麼。將推估 CO2 稱為管理估算，不稱為正式查證碳權。",
    "回答最後加一行「依據：」，列出 1–3 個使用到的樹號或統計值。",
    JSON.stringify(context),
  ].join("\n");
}
