import { openAsBlob, createReadStream, createWriteStream } from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";

export function validateCloudEndpoint(value, apiKey) {
  const url = new URL(value);
  const local = ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname);
  if (url.username || url.password || url.search || url.hash || (!local && url.protocol !== "https:") || !["https:", "http:"].includes(url.protocol)) throw new Error("雲端網址必須為 HTTPS，且不得包含帳密或查詢參數");
  if (!local && !apiKey) throw new Error("遠端量測服務必須設定伺服器端 API key");
  return url.href.replace(/\/+$/, "");
}

export function validateCloudResult(status) {
  if (status.status !== "succeeded" || status.prepare_only !== false || status.execution?.mode !== "full" || status.execution?.pipeline !== "arbor3d") throw new Error("雲端只完成資料準備，尚未完成正式量測");
  if (!status.result || !/^[a-f0-9]{64}$/.test(status.result.sha256) || !Number.isSafeInteger(status.result.bytes) || status.result.bytes <= 0 || status.result.bytes > 6 * 1024 ** 3) throw new Error("雲端量測缺少可驗證的成果檔");
}

function python(args, repoRoot) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.env.PYTHON || (process.platform === "win32" ? "python" : "python3"), ["-m", "cloud_dbh.archives", ...args], {
      cwd: repoRoot, windowsHide: true, stdio: ["ignore", "inherit", "inherit"], env: process.env,
    });
    child.once("error", reject);
    child.once("exit", code => code === 0 ? resolve() : reject(new Error(`雲端成果整理失敗（${code}）`)));
  });
}

export async function runCloudDbh({ baseUrl, apiKey = "", jobDir, scanId, pathId = "", appRoot, request = fetch, log = console.log }) {
  const base = validateCloudEndpoint(baseUrl, apiKey);
  const headers = apiKey ? { "X-API-Key": apiKey } : {};
  const capsResponse = await request(`${base}/v1/capabilities`, { headers, signal: AbortSignal.timeout(30000) });
  if (!capsResponse.ok) throw new Error(`雲端能力檢查失敗（${capsResponse.status}）`);
  const caps = await capsResponse.json();
  if (!caps.full_pipeline_ready || caps.prepare_only || !caps.result_download) throw new Error("Azure 目前僅備妥資料整理服務，尚不能執行正式量測");
  const temporary = await fs.mkdtemp(path.join(os.tmpdir(), "arbor3d-cloud-"));
  try {
    const repoRoot = path.resolve(appRoot, "..");
    let previous;
    try { previous = JSON.parse(await fs.readFile(path.join(jobDir, "cloud-job.json"), "utf8")); }
    catch (error) { if (error.code !== "ENOENT") throw new Error("既有雲端任務紀錄無法讀取，請先確認任務狀態"); }
    let jobId;
    if (previous?.base === base && previous.scanId === scanId && /^[a-f0-9]{32}$/.test(previous.jobId)) {
      const response = await request(`${base}/v1/jobs/${previous.jobId}`, { headers, signal: AbortSignal.timeout(30000) });
      if (response.ok) {
        const status = await response.json();
        if (["queued", "running", "succeeded"].includes(status.status)) jobId = previous.jobId;
      } else if (response.status !== 404) throw new Error("無法確認既有雲端任務，已停止重複提交");
    }
    if (!jobId) {
      const archive = path.join(temporary, "upload.zip");
      await python(["pack", "--inbox", jobDir, "--archive", archive], repoRoot);
      const size = (await fs.stat(archive)).size;
      if (size > caps.max_upload_bytes) throw new Error("本批資料超過雲端上傳限制，請分批處理");
      const form = new FormData();
      form.set("scan_id", scanId); form.set("path_id", pathId);
      form.set("archive", await openAsBlob(archive, { type: "application/zip" }), "input.zip");
      const response = await request(`${base}/v1/jobs`, { method: "POST", headers, body: form, signal: AbortSignal.timeout(15 * 60000) });
      if (!response.ok) throw new Error(`雲端任務提交失敗（${response.status}）`);
      const created = await response.json();
      if (!/^[a-f0-9]{32}$/.test(created.job_id)) throw new Error("雲端任務編號不正確");
      jobId = created.job_id;
      await fs.writeFile(path.join(jobDir, "cloud-job.json"), JSON.stringify({ jobId, scanId, base, submittedAt: new Date().toISOString() }));
    }
    const deadline = Date.now() + 60 * 60000;
    while (Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 3000));
      const poll = await request(`${base}/v1/jobs/${jobId}`, { headers, signal: AbortSignal.timeout(30000) });
      if (!poll.ok) throw new Error(`雲端任務查詢失敗（${poll.status}），任務編號已保留`);
      const status = await poll.json();
      log(`雲端任務 ${jobId}：${status.status}`);
      if (status.status === "failed") throw new Error("Azure 量測未完成，請查看雲端任務紀錄");
      if (status.status === "prepared") throw new Error("雲端只完成輸入準備，不是正式量測成果");
      if (status.status !== "succeeded") continue;
      validateCloudResult(status);
      const resultResponse = await request(`${base}/v1/jobs/${jobId}/result`, { headers, signal: AbortSignal.timeout(15 * 60000) });
      if (!resultResponse.ok || !resultResponse.body) throw new Error("雲端成果下載失敗");
      const resultFile = path.join(temporary, "result.zip");
      let received = 0;
      await pipeline(Readable.fromWeb(resultResponse.body), async function* (source) {
        for await (const chunk of source) {
          received += chunk.length;
          if (received > status.result.bytes) throw new Error("雲端成果超過宣告大小");
          yield chunk;
        }
      }, createWriteStream(resultFile));
      if ((await fs.stat(resultFile)).size !== status.result.bytes) throw new Error("雲端成果大小不符");
      const hash = createHash("sha256");
      for await (const chunk of createReadStream(resultFile)) hash.update(chunk);
      if (hash.digest("hex") !== status.result.sha256) throw new Error("雲端成果校驗失敗");
      await python(["install", "--archive", resultFile, "--app-root", appRoot, "--scan-id", scanId, "--path-id", pathId], repoRoot);
      await fs.writeFile(path.join(jobDir, "pipeline-status.json"), JSON.stringify({ status: "done", message: "遠端正式量測成果已下載並核對", cloud_job_id: jobId, execution: status.execution }));
      return;
    }
    throw new Error("雲端任務查詢逾時，任務編號已保留");
  } finally {
    // This path is created here by mkdtemp; never remove an input or output directory.
    if (path.dirname(temporary) === path.resolve(os.tmpdir()) && path.basename(temporary).startsWith("arbor3d-cloud-")) await fs.rm(temporary, { recursive: true, force: true });
  }
}
