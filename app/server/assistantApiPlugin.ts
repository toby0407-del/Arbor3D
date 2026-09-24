import type { IncomingMessage, ServerResponse } from "node:http";
import type { Plugin } from "vite";
import {
  assistantSystemPrompt,
  localAssistantReply,
  type AssistantContext,
  type AssistantReply,
} from "./assistantCore.js";
import {
  countKnowledgeQuestions,
  ragPrompt,
  retrieveKnowledge,
  type RagHit,
} from "./localRag.js";

const MAX_BODY_BYTES = 256 * 1024;
const DIRECT_LINE_BASE = "https://directline.botframework.com/v3/directline";

function sendJson(res: ServerResponse, status: number, body: unknown) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(body));
}

async function readJson(req: IncomingMessage) {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += buffer.length;
    if (size > MAX_BODY_BYTES) throw new Error("請求內容過大");
    chunks.push(buffer);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8")) as {
    question?: unknown;
    context?: unknown;
  };
}

function validContext(value: unknown): value is AssistantContext {
  if (!value || typeof value !== "object") return false;
  const context = value as Partial<AssistantContext>;
  return (
    typeof context.scanId === "string" &&
    typeof context.parkName === "string" &&
    typeof context.pathName === "string" &&
    Array.isArray(context.trees) &&
    context.trees.length <= 500 &&
    Boolean(context.summary && typeof context.summary.total === "number")
  );
}

function azureUrl(endpoint: string) {
  const base = endpoint.replace(/\/+$/, "");
  return base.includes("/openai/v1")
    ? `${base}/chat/completions`
    : `${base}/openai/v1/chat/completions`;
}

function foundryLocalUrl(endpoint: string) {
  const url = new URL(endpoint);
  if (!["localhost", "127.0.0.1", "::1"].includes(url.hostname)) {
    throw new Error("Foundry Local endpoint 只允許本機 loopback 位址");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("Foundry Local endpoint 必須使用 HTTP 或 HTTPS");
  }
  const base = url.toString().replace(/\/+$/, "");
  return base.endsWith("/v1")
    ? `${base}/chat/completions`
    : `${base}/v1/chat/completions`;
}

type DirectLineToken = {
  token?: string;
  conversationId?: string;
};

type DirectLineActivity = {
  type?: string;
  text?: string;
  from?: { id?: string; name?: string };
};

const assistantEvidence = (context: AssistantContext) => [
  `掃描 ${context.scanId}，${context.summary.total} 棵`,
  `較可信 ${context.summary.reliable}、待確認 ${context.summary.pending}、需複核 ${context.summary.review}`,
];

export async function askPhi4Local(
  question: string,
  context: AssistantContext,
  env: Record<string, string | undefined>,
  ragHits: RagHit[],
): Promise<AssistantReply | null> {
  const endpoint = env.FOUNDRY_LOCAL_ENDPOINT?.trim();
  if (!endpoint) return null;
  const model = env.FOUNDRY_LOCAL_MODEL?.trim() || "phi-4-mini";
  const response = await fetch(foundryLocalUrl(endpoint), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      temperature: 0.2,
      max_tokens: 500,
      messages: [
        { role: "system", content: assistantSystemPrompt(context, ragPrompt(ragHits)) },
        { role: "user", content: question },
      ],
    }),
    signal: AbortSignal.timeout(60_000),
  });
  if (!response.ok) {
    const detail = (await response.text()).slice(0, 400);
    throw new Error(`Phi-4 本機模型回應 ${response.status}：${detail}`);
  }
  const data = (await response.json()) as {
    choices?: Array<{ message?: { content?: string } }>;
  };
  const answer = data.choices?.[0]?.message?.content?.trim();
  if (!answer) throw new Error("Phi-4 本機模型沒有回傳文字");
  return {
    provider: "phi4",
    model,
    answer,
    evidence: assistantEvidence(context),
    ragSources: ragHits.map((hit) => `${hit.source}:${hit.line}`),
  };
}

export async function askCopilotStudio(
  question: string,
  context: AssistantContext,
  env: Record<string, string | undefined>,
  ragHits: RagHit[],
): Promise<AssistantReply | null> {
  const tokenEndpoint = env.COPILOT_STUDIO_TOKEN_ENDPOINT?.trim();
  const allowed = env.ARBOR_ALLOW_BILLABLE_CLOUD === "YES_I_ACCEPT_COSTS";
  if (!tokenEndpoint || !allowed) return null;
  if (!/^https:\/\//i.test(tokenEndpoint)) {
    throw new Error("Copilot Studio Token Endpoint 必須使用 HTTPS");
  }

  const tokenResponse = await fetch(tokenEndpoint, {
    method: "GET",
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(30_000),
  });
  if (!tokenResponse.ok) {
    throw new Error(`Copilot Studio Token Endpoint 回應 ${tokenResponse.status}`);
  }
  const tokenData = (await tokenResponse.json()) as DirectLineToken;
  if (!tokenData.token) throw new Error("Copilot Studio 沒有回傳 Direct Line token");
  const authorization = { Authorization: `Bearer ${tokenData.token}` };

  let conversationId = tokenData.conversationId;
  if (!conversationId) {
    const conversationResponse = await fetch(`${DIRECT_LINE_BASE}/conversations`, {
      method: "POST",
      headers: authorization,
      signal: AbortSignal.timeout(30_000),
    });
    if (!conversationResponse.ok) {
      throw new Error(`Copilot Studio 無法建立對話：${conversationResponse.status}`);
    }
    const conversation = (await conversationResponse.json()) as DirectLineToken;
    conversationId = conversation.conversationId;
  }
  if (!conversationId) throw new Error("Copilot Studio 沒有回傳 conversationId");

  const appUserId = `arbor3d-${context.scanId.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
  const activityUrl = `${DIRECT_LINE_BASE}/conversations/${encodeURIComponent(conversationId)}/activities`;
  const prompt = [
    assistantSystemPrompt(context, ragPrompt(ragHits)),
    `使用者問題：${question}`,
  ].join("\n\n");
  const activityResponse = await fetch(activityUrl, {
    method: "POST",
    headers: { ...authorization, "Content-Type": "application/json" },
    body: JSON.stringify({
      type: "message",
      from: { id: appUserId, name: "Arbor3D App" },
      locale: "zh-TW",
      text: prompt,
    }),
    signal: AbortSignal.timeout(30_000),
  });
  if (!activityResponse.ok) {
    throw new Error(`Copilot Studio 無法送出訊息：${activityResponse.status}`);
  }

  const deadline = Date.now() + 25_000;
  while (Date.now() < deadline) {
    const activitiesResponse = await fetch(activityUrl, {
      method: "GET",
      headers: { ...authorization, Accept: "application/json" },
      signal: AbortSignal.timeout(30_000),
    });
    if (!activitiesResponse.ok) {
      throw new Error(`Copilot Studio 無法讀取回答：${activitiesResponse.status}`);
    }
    const activitiesData = (await activitiesResponse.json()) as {
      activities?: DirectLineActivity[];
    };
    const answer = [...(activitiesData.activities ?? [])]
      .reverse()
      .find((activity) =>
        activity.type === "message" &&
        activity.from?.id !== appUserId &&
        Boolean(activity.text?.trim()),
      )?.text?.trim();
    if (answer) {
      return {
        provider: "copilot",
        model: env.COPILOT_STUDIO_AGENT_NAME?.trim() || "Microsoft Copilot Studio",
        answer,
        evidence: assistantEvidence(context),
        ragSources: ragHits.map((hit) => `${hit.source}:${hit.line}`),
      };
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("Copilot Studio 回答逾時");
}

async function askAzure(
  question: string,
  context: AssistantContext,
  env: Record<string, string | undefined>,
  ragHits: RagHit[],
): Promise<AssistantReply | null> {
  const endpoint = env.AZURE_AI_ENDPOINT?.trim();
  const apiKey = env.AZURE_AI_API_KEY?.trim();
  const model =
    env.AZURE_AI_MODEL?.trim() ||
    env.FOUNDRY_MODEL_DEPLOYMENT?.trim();
  const allowed =
    env.ARBOR_ALLOW_BILLABLE_CLOUD === "YES_I_ACCEPT_COSTS";
  if (!endpoint || !model || !allowed) return null;
  if (!/^https:\/\//i.test(endpoint)) throw new Error("Azure endpoint 必須使用 HTTPS");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (apiKey) {
    headers["api-key"] = apiKey;
  } else {
    const { DefaultAzureCredential } = await import("@azure/identity");
    const credential = new DefaultAzureCredential();
    const token = await credential.getToken(
      "https://ai.azure.com/.default",
    );
    if (!token?.token) throw new Error("無法取得 Azure 身分權杖");
    headers.Authorization = `Bearer ${token.token}`;
  }

  const response = await fetch(azureUrl(endpoint), {
    method: "POST",
    headers,
    body: JSON.stringify({
      model,
      temperature: 0.2,
      max_tokens: 500,
      messages: [
        { role: "system", content: assistantSystemPrompt(context, ragPrompt(ragHits)) },
        { role: "user", content: question },
      ],
    }),
    signal: AbortSignal.timeout(30_000),
  });
  if (!response.ok) {
    const detail = (await response.text()).slice(0, 400);
    throw new Error(`Azure AI 回應 ${response.status}：${detail}`);
  }
  const data = (await response.json()) as {
    choices?: Array<{ message?: { content?: string } }>;
  };
  const answer = data.choices?.[0]?.message?.content?.trim();
  if (!answer) throw new Error("Azure AI 沒有回傳文字");
  return {
    provider: "azure",
    model,
    answer,
    evidence: assistantEvidence(context),
    ragSources: ragHits.map((hit) => `${hit.source}:${hit.line}`),
  };
}

export function assistantProviderStatus(env: Record<string, string | undefined> = process.env) {
  const configured = (env.ARBOR_AI_PROVIDER?.trim().toLowerCase() || "phi4") as string;
  const provider = ["auto", "phi4", "copilot", "azure", "local"].includes(configured)
    ? configured
    : "phi4";
  const billable = env.ARBOR_ALLOW_BILLABLE_CLOUD === "YES_I_ACCEPT_COSTS";
  const phi4Ready = Boolean(env.FOUNDRY_LOCAL_ENDPOINT?.trim());
  const copilotEndpoint = Boolean(env.COPILOT_STUDIO_TOKEN_ENDPOINT?.trim());
  const azureReady = Boolean(env.AZURE_AI_ENDPOINT?.trim() && env.AZURE_AI_MODEL?.trim());
  return {
    provider,
    billableAllowed: billable,
    phi4Configured: phi4Ready,
    copilotConfigured: copilotEndpoint,
    azureConfigured: azureReady,
    activeMode:
      provider === "local"
        ? "local"
        : provider === "phi4" && phi4Ready
          ? "phi4"
        : provider === "copilot" && copilotEndpoint && billable
          ? "copilot"
          : provider === "azure" && azureReady && billable
            ? "azure"
            : provider === "auto" && phi4Ready
              ? "phi4"
              : provider === "auto" && copilotEndpoint && billable
              ? "copilot"
              : provider === "auto" && azureReady && billable
                ? "azure"
                : "local",
    hints: [
      provider === "phi4" && !phi4Ready
        ? "尚未填 FOUNDRY_LOCAL_ENDPOINT；請先在 Windows 啟動 Foundry Local 與 Phi-4"
        : null,
      !copilotEndpoint
        ? "尚未填 COPILOT_STUDIO_TOKEN_ENDPOINT（Copilot Studio → Channels → Mobile app）"
        : null,
      !billable
        ? "ARBOR_ALLOW_BILLABLE_CLOUD 未開啟，雲端 Copilot／Azure AI 不會計費呼叫"
        : null,
      "現場手測資料庫：設定 AZURE_COSMOS_ENDPOINT 時用 Cosmos FieldMeasures；盤點本體仍是 App JSON 檔",
    ].filter(Boolean),
  };
}

export function assistantApiPlugin(
  env: Record<string, string | undefined> = process.env,
  knowledgeFolder = "",
): Plugin {
  return {
    name: "arbor3d-assistant-api",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = req.url?.split("?")[0] ?? "";
        if (url === "/api/assistant/status" && req.method === "GET") {
          sendJson(res, 200, assistantProviderStatus(env));
          return;
        }
        if (url !== "/api/assistant") return next();
        if (req.method !== "POST") {
          sendJson(res, 405, { error: "只接受 POST" });
          return;
        }
        try {
          const body = await readJson(req);
          const question =
            typeof body.question === "string" ? body.question.trim() : "";
          if (!question || question.length > 500 || !validContext(body.context)) {
            sendJson(res, 400, { error: "問題或盤點內容格式不正確" });
            return;
          }
          const context = body.context;
          const folder = env.ARBOR_RAG_KNOWLEDGE?.trim() || knowledgeFolder;
          const ragHits = folder ? retrieveKnowledge(question, folder) : [];
          const ragQuestionCount = folder ? countKnowledgeQuestions(folder) : 0;
          const configuredProvider = env.ARBOR_AI_PROVIDER?.trim().toLowerCase();
          const provider = ["auto", "phi4", "copilot", "azure", "local"].includes(configuredProvider ?? "")
            ? configuredProvider
            : "phi4";
          let reply: AssistantReply | null = null;
          let cloudFailed = false;
          let localModelFailed = false;
          if (provider === "auto" || provider === "phi4") {
            try {
              reply = await askPhi4Local(question, context, env, ragHits);
            } catch {
              localModelFailed = true;
            }
          }
          if (provider === "auto" || provider === "copilot") {
            try {
              reply = await askCopilotStudio(question, context, env, ragHits);
            } catch {
              cloudFailed = true;
            }
          }
          if (!reply && (provider === "auto" || provider === "azure")) {
            try {
              reply = await askAzure(question, context, env, ragHits);
            } catch {
              cloudFailed = true;
            }
          }
          if (!reply) {
            reply = localAssistantReply(question, context);
            if (localModelFailed) {
              reply.answer += "\n\n（Phi-4 本機模型暫時無法使用，已切換成本機證據回答。）";
            } else if (cloudFailed) {
              reply.answer += "\n\n（Microsoft 雲端 AI 暫時無法使用，已切換成本機證據回答。）";
            } else if (provider === "copilot") {
              reply.answer += "\n\n（Copilot Studio 尚未設定或費用鎖未開啟，已使用本機證據回答。）";
            }
          }
          if (ragHits.length && !reply.ragSources?.length) {
            reply.ragSources = ragHits.map((hit) => `${hit.source}:${hit.line}`);
            reply.evidence.push(...reply.ragSources.map((source) => `本機 RAG：${source}`));
          }
          if (ragQuestionCount) reply.ragQuestionCount = ragQuestionCount;
          sendJson(res, 200, reply);
        } catch (error) {
          sendJson(res, 400, {
            error: error instanceof Error ? error.message : "無法處理請求",
          });
        }
      });
    },
  };
}
