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
    evidence: [
      `掃描 ${context.scanId}，${context.summary.total} 棵`,
      `較可信 ${context.summary.reliable}、待確認 ${context.summary.pending}、需複核 ${context.summary.review}`,
    ],
    ragSources: ragHits.map((hit) => `${hit.source}:${hit.line}`),
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
          let reply: AssistantReply;
          try {
            reply =
              (await askAzure(question, context, env, ragHits)) ??
              localAssistantReply(question, context);
          } catch {
            reply = localAssistantReply(question, context);
            reply.answer += "\n\n（Azure AI 暫時無法使用，已切換成本機證據回答。）";
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
