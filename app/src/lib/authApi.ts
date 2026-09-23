import type { Session } from "./session";

export type AccountList = {
  accounts: Session[];
  demo: boolean;
  mode: "entra" | "demo";
  storage: "cosmos" | "file";
};

const entra = {
  clientId: import.meta.env.VITE_AZURE_ENTRA_CLIENT_ID?.trim() ?? "",
  tenantId: import.meta.env.VITE_AZURE_ENTRA_TENANT_ID?.trim() ?? "",
  scope: import.meta.env.VITE_AZURE_ENTRA_SCOPE?.trim() ?? "",
};
let msalClient: Promise<import("@azure/msal-browser").PublicClientApplication> | null = null;

function getMsalClient() {
  if (!msalClient) {
    msalClient = import("@azure/msal-browser").then(async ({ PublicClientApplication }) => {
      const client = new PublicClientApplication({
        auth: {
          clientId: entra.clientId,
          authority: `https://login.microsoftonline.com/${entra.tenantId}`,
          redirectUri: window.location.origin,
        },
        cache: { cacheLocation: "sessionStorage" },
      });
      await client.initialize();
      return client;
    });
  }
  return msalClient;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    credentials: "same-origin",
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body = await response.json() as T & { error?: string };
  if (!response.ok) throw new Error(body.error || "帳號服務暫時無法使用");
  return body;
}

export const fetchAccounts = () => request<AccountList>("/api/auth/accounts");

export const login = (workId: string, password: string) =>
  request<Session>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ workId, password }),
  });

export const demoLogin = (workId: string) =>
  request<Session>("/api/auth/demo-login", {
    method: "POST",
    body: JSON.stringify({ workId }),
  });

export async function entraLogin() {
  if (!entra.clientId || !entra.tenantId || !entra.scope) {
    throw new Error("Microsoft Entra ID 前端設定不完整");
  }
  const client = await getMsalClient();
  const result = await client.loginPopup({ scopes: [entra.scope] });
  if (!result.accessToken) throw new Error("Microsoft Entra ID 沒有回傳 API access token");
  return request<Session>("/api/auth/entra", {
    method: "POST",
    headers: { Authorization: `Bearer ${result.accessToken}` },
  });
}

export const currentSession = () => request<Session>("/api/auth/me");

export async function logout() {
  const result = await request<{ ok: boolean }>("/api/auth/logout", { method: "POST" });
  if (entra.clientId && entra.tenantId && msalClient) {
    await (await msalClient).clearCache();
  }
  return result;
}
