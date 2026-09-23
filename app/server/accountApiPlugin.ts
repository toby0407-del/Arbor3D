import { randomBytes } from "node:crypto";
import type { IncomingMessage, ServerResponse } from "node:http";
import { createRemoteJWKSet, jwtVerify, type JWTPayload } from "jose";
import type { Plugin } from "vite";
import { createFieldMeasureStore, type FieldMeasureRecord } from "./fieldMeasureStore.js";

const COOKIE = "arbor3d_session";
const SESSION_MS = 8 * 60 * 60 * 1000;
const MAX_BODY_BYTES = 256 * 1024;

type Account = {
  workId: string;
  name: string;
  role: string;
  password: string;
};

type SessionRecord = {
  account: Omit<Account, "password">;
  expiresAt: number;
};

const DEMO_ACCOUNTS: Account[] = [
  { workId: "E-1027", name: "林志偉", role: "現場調查員", password: "arbor1027" },
  { workId: "E-2041", name: "陳雅婷", role: "複核人員", password: "arbor2041" },
  { workId: "E-3308", name: "黃建宏", role: "承辦人", password: "arbor3308" },
];

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
  return JSON.parse(Buffer.concat(chunks).toString("utf8")) as Record<string, unknown>;
}

function cookieValue(req: IncomingMessage, name: string) {
  for (const item of (req.headers.cookie ?? "").split(";")) {
    const [key, ...parts] = item.trim().split("=");
    if (key === name) return decodeURIComponent(parts.join("="));
  }
  return "";
}

function publicAccount(account: Account | Omit<Account, "password">) {
  return { workId: account.workId, name: account.name, role: account.role };
}

function validMeasures(value: unknown): value is FieldMeasureRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const rows = Object.entries(value);
  if (rows.length > 500) return false;
  return rows.every(([treeId, raw]) => {
    if (!/^[\w.-]{1,100}$/.test(treeId) || !raw || typeof raw !== "object") return false;
    const item = raw as Partial<FieldMeasureRecord[string]>;
    return [item.dbhCm, item.heightM, item.coeff, item.measuredAt]
      .every((field) => typeof field === "string" && field.length <= 40) &&
      typeof item.note === "string" && item.note.length <= 500 &&
      (item.strict13m == null || typeof item.strict13m === "boolean");
  });
}

export function sessionAccountFromClaims(payload: JWTPayload) {
  const roles = Array.isArray(payload.roles)
    ? payload.roles.filter((role): role is string => typeof role === "string")
    : [];
  const workId = typeof payload.preferred_username === "string"
    ? payload.preferred_username
    : typeof payload.oid === "string" ? payload.oid : "";
  const name = typeof payload.name === "string" ? payload.name : workId;
  if (!workId || !name) throw new Error("Entra token 缺少使用者識別資料");
  return { workId, name, role: roles[0] || "盤點人員" };
}

export function accountApiPlugin(
  root: string,
  env: Record<string, string | undefined> = process.env,
): Plugin {
  const sessions = new Map<string, SessionRecord>();
  const measureStore = createFieldMeasureStore(root, env);
  const tenantId = env.AZURE_ENTRA_TENANT_ID?.trim();
  const audience = env.AZURE_ENTRA_API_AUDIENCE?.trim() || env.AZURE_ENTRA_CLIENT_ID?.trim();
  const entraConfigured = Boolean(tenantId && audience);
  const jwks = tenantId
    ? createRemoteJWKSet(new URL(`https://login.microsoftonline.com/${tenantId}/discovery/v2.0/keys`))
    : null;

  const getSession = (req: IncomingMessage) => {
    const token = cookieValue(req, COOKIE);
    const session = token ? sessions.get(token) : undefined;
    if (!session) return null;
    if (session.expiresAt <= Date.now()) {
      sessions.delete(token);
      return null;
    }
    return session;
  };

  const startSession = (req: IncomingMessage, res: ServerResponse, account: SessionRecord["account"]) => {
    const token = randomBytes(32).toString("base64url");
    sessions.set(token, { account, expiresAt: Date.now() + SESSION_MS });
    const secure = req.headers["x-forwarded-proto"] === "https" ? "; Secure" : "";
    res.setHeader("Set-Cookie", `${COOKIE}=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${SESSION_MS / 1000}${secure}`);
    sendJson(res, 200, account);
  };

  return {
    name: "arbor3d-account-api",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const requestUrl = new URL(req.url ?? "/", "http://localhost");
        const url = requestUrl.pathname;
        const managed = url.startsWith("/api/auth/") || url === "/api/field-measures";
        if (!managed) {
          const formalMode = entraConfigured;
          const protectedApi = url === "/api/assistant" || url.startsWith("/api/import");
          if (!formalMode || !protectedApi) return next();
          const session = getSession(req);
          if (!session) {
            sendJson(res, 401, { error: "登入已失效" });
            return;
          }
          if (url.startsWith("/api/import") && req.method !== "GET") {
            const roles = (env.ARBOR_IMPORT_ROLES ?? "管理者,承辦人")
              .split(",").map((item) => item.trim()).filter(Boolean);
            if (!roles.includes(session.account.role)) {
              sendJson(res, 403, { error: "此角色沒有匯入盤點資料的權限" });
              return;
            }
          }
          return next();
        }
        try {
          if (url === "/api/auth/accounts" && req.method === "GET") {
            sendJson(res, 200, {
              accounts: entraConfigured ? [] : DEMO_ACCOUNTS.map(publicAccount),
              demo: !entraConfigured,
              mode: entraConfigured ? "entra" : "demo",
              storage: measureStore.provider,
            });
            return;
          }
          if (url === "/api/auth/me" && req.method === "GET") {
            const session = getSession(req);
            sendJson(res, session ? 200 : 401, session ? session.account : { error: "尚未登入" });
            return;
          }
          if (url === "/api/auth/logout" && req.method === "POST") {
            const token = cookieValue(req, COOKIE);
            if (token) sessions.delete(token);
            res.setHeader("Set-Cookie", `${COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0`);
            sendJson(res, 200, { ok: true });
            return;
          }
          if (url === "/api/auth/entra" && req.method === "POST") {
            if (!entraConfigured || !tenantId || !audience || !jwks) {
              sendJson(res, 400, { error: "Microsoft Entra ID 尚未設定" });
              return;
            }
            const bearer = req.headers.authorization?.match(/^Bearer\s+(.+)$/i)?.[1];
            if (!bearer) {
              sendJson(res, 401, { error: "缺少 Entra access token" });
              return;
            }
            const { payload } = await jwtVerify(bearer, jwks, {
              audience,
              issuer: `https://login.microsoftonline.com/${tenantId}/v2.0`,
            });
            startSession(req, res, sessionAccountFromClaims(payload));
            return;
          }
          if ((url === "/api/auth/login" || url === "/api/auth/demo-login") && req.method === "POST") {
            if (entraConfigured) {
              sendJson(res, 404, { error: "正式環境只接受 Microsoft Entra ID" });
              return;
            }
            const body = await readJson(req);
            const workId = typeof body.workId === "string" ? body.workId.trim() : "";
            const password = typeof body.password === "string" ? body.password : "";
            const account = DEMO_ACCOUNTS.find((item) => item.workId === workId);
            const valid = account && (url === "/api/auth/demo-login" || account.password === password);
            if (!account || !valid) {
              sendJson(res, 401, { error: "帳號或密碼不正確" });
              return;
            }
            startSession(req, res, publicAccount(account));
            return;
          }

          const session = getSession(req);
          if (!session) {
            sendJson(res, 401, { error: "登入已失效" });
            return;
          }
          const scanId = requestUrl.searchParams.get("scanId")?.trim() ?? "";
          if (!/^[\w.-]{1,100}$/.test(scanId)) {
            sendJson(res, 400, { error: "scanId 格式不正確" });
            return;
          }
          if (req.method === "GET") {
            sendJson(res, 200, {
              measures: await measureStore.read(scanId),
              storage: measureStore.provider,
            });
            return;
          }
          if (req.method === "PUT") {
            const body = await readJson(req);
            if (!validMeasures(body.measures)) {
              sendJson(res, 400, { error: "人工量測格式不正確" });
              return;
            }
            await measureStore.write(scanId, body.measures, {
              updatedAt: new Date().toISOString(),
              updatedBy: session.account.workId,
            });
            sendJson(res, 200, { ok: true, storage: measureStore.provider });
            return;
          }
          sendJson(res, 405, { error: "不支援的方法" });
        } catch (error) {
          const code = (error as { code?: string }).code ?? "";
          const tokenError = code.startsWith("ERR_JWT") || code.startsWith("ERR_JWS") || code.startsWith("ERR_JWK");
          sendJson(res, tokenError ? 401 : 500, {
            error: tokenError
              ? "Microsoft Entra access token 驗證失敗"
              : error instanceof Error ? error.message : "伺服器錯誤",
          });
        }
      });
    },
  };
}
