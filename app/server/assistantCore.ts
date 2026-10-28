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
  trees: AssistantTree[];
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
        answer: `需複核 ${context.summary.review} 棵、待確認 ${context.summary.pending} 棵，合計 ${reviewTrees.length} 棵待人工核對。建議先處理：${reasons.join("、")}。先做 1.3 m 標準胸高人工量測，再補拍遮擋嚴重的樹幹。`,
      evidence: [...evidence, `待處理樹號：${listTrees(reviewTrees)}`],
    };
  }

  if (/碳|co2|co₂|碳匯|排放/.test(q)) {
    return {
      provider: "local",
      answer: `本次候選 CO₂ 當量試算合計約 ${fmt(context.summary.co2Ton)} ton，包含待複核尺寸與可能推估的樹高。這是由胸徑、樹高與係數估算的管理指標，不是已驗證總碳量；樹高或係數尚未實測時，不應作為正式碳權或查證數字。`,
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
    answer: `這次在「${context.parkName}／${context.pathName}」盤點 ${context.summary.total} 棵樹，其中較可信 ${context.summary.reliable} 棵，待確認 ${context.summary.pending} 棵，需複核 ${context.summary.review} 棵。可先核對異常樹木，再查看 App 內的本機 Power BI 分析。`,
    evidence,
  };
}

export function assistantSystemPrompt(context: AssistantContext, ragContext = "", question = "") {
  const pairs = context.trees.filter(tree => tree.manualDbhCm != null && tree.dbhCm != null).length;
  const red=context.trees.filter(t=>t.status==='red');
  const yellow=context.trees.filter(t=>t.status==='yellow');
  const largest=context.trees.filter(t=>t.dbhCm!=null).sort((a,b)=>b.dbhCm!-a.dbhCm!)[0];
  const requested=question.match(/Tree_\d+/gi)??[];
  const specific=requested.map(id=>context.trees.find(t=>t.id.toLowerCase()===id.toLowerCase())??{id,dbhCm:null,missing:true});
  const treeFacts=specific.length?specific.map(t=>'missing' in t?`查無樹號 ${t.id}，沒有可用數值。`:`${t.id} 胸徑 ${t.dbhCm??'缺值'} cm。`):
    /最大|最粗|胸徑最大/.test(question)&&largest?[`胸徑最大樹號 ${largest.id}；胸徑 ${largest.dbhCm} cm。`]:[];
  return [
    "你是 Arbor3D 樹木盤點助理。只用繁體中文，用 1 至 4 句回答，最多 180 字。不要輸出 JSON、程式欄位或重複步驟。",
    "以下已核對事實優先於參考文件。不要從信心、弧度或備註自行推斷複核名單。不可捏造配對、樹木、健康診斷、跨期實測或碳權。",
    ragContext,
    '【本次已核對事實】',
    `地點：${context.parkName}。總數 ${context.summary.total} 棵；較可信 ${context.summary.reliable} 棵；待確認 ${yellow.length} 棵；需複核 ${red.length} 棵；兩類合計 ${yellow.length+red.length} 棵需人工核對。`,
    `需複核樹號（完整名單）：${red.map(t=>t.id).join('、')||'無'}。待確認樹號：${yellow.map(t=>t.id).join('、')||'無'}。不要將兩個數量混稱為「需複核」。`,
    `有效人工配對 ${context.datasetKind==='simulated'?0:pairs} 筆。${context.datasetKind==='simulated'||pairs===0?'沒有有效實測配對；MAE、準確率未驗證，不得編造任何配對。':''}`,
    `候選 CO₂ 存量估算 ${fmt(context.summary.co2Ton)} t；不是年度吸收量或已認證碳權。`,
    ...treeFacts,
    /優先.*複核|哪些.*複核/.test(question)?`本題請具體回答優先核對樹號：${[...red,...yellow].slice(0,5).map(t=>t.id).join('、')||'無'}。不要只回答紅燈、低信心或遮擋等泛稱，也不要自行新增樹號。`:'',
    /power\s*bi|fabric/i.test(question)?'本系統使用 Power BI Desktop 在電腦分析，再把成果更新至 Arbor3D App。不需登入或 Fabric。確切操作步驟由系統另外顯示，你只需一句話解釋本機流程，不要自行創造按鈕或重寫檔名。':'',
    '回答只使用上述事實及相關參考；查無樹號就直說查無資料。結尾一行「依據：」列出實際使用的數字或樹號。',
  ].filter(Boolean).join("\n");
}
