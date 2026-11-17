// Explicit, read-only application check. Does not insert tree measurements.
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { inventoryAssistantContext } from "../src/lib/assistant.ts";
import type { ParkInventoryReport } from "../src/types.ts";

const base = "http://127.0.0.1:5324";
const login = await fetch(`${base}/api/auth/demo-login`, {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ workId: "E-1027" }),
});
if (!login.ok) throw new Error("Local account login is unavailable; use the configured organization login.");
const cookie = login.headers.get("set-cookie")?.split(";")[0];
if (!cookie) throw new Error("No session established");
const headers = { cookie, "Content-Type": "application/json" };
const services = await fetch(`${base}/api/auth/services`, { headers }).then(r=>r.json());
const report = JSON.parse(await readFile(new URL("../src/data/inventories/20260818092855.json", import.meta.url), "utf8")) as ParkInventoryReport;
const context = inventoryAssistantContext("逢甲大學", "既有掃描路線", report, {});
const start = Date.now();
const response = await fetch(`${base}/api/assistant`, { method: "POST", headers,
  body: JSON.stringify({ question: "這批資料能宣稱已經驗證胸徑精度嗎？請用繁體中文簡短回答。", context }),
  signal: AbortSignal.timeout(90000),
});
const reply = await response.json();
if (!response.ok || reply.provider !== "phi4" || !reply.answer?.trim()) throw new Error(JSON.stringify(reply));
const status = await fetch(`${base}/api/assistant/status`, { headers }).then(r=>r.json());
await fetch(`${base}/api/auth/logout`, { method: "POST", headers });
const verification = { verifiedAt: new Date().toISOString(), services, status,
  inference: { ...reply, elapsedMs: Date.now()-start }, scanId: report.scan_id };
await mkdir("../.runtime", { recursive: true });
await writeFile("../.runtime/microsoft-verification.json", JSON.stringify(verification, null, 2));
console.log(JSON.stringify({ services, provider: reply.provider, model: reply.model,
  answer: reply.answer, elapsedMs: verification.inference.elapsedMs, connection: status.connection }, null, 2));
