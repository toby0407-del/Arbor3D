/**
 * 後續量測處理：去噪 + 高斯濺射就緒後執行。
 *
 * 環境變數（擇一，優先順序由上到下）：
 *   ARBOR3D_CLOUD_DBH_URL — Azure／本機 Cloud DBH HTTP 服務根網址
 *   ARBOR3D_CMD           — 完整指令，會代入 {jobDir} {scanId} {pathId}
 *   ARBOR3D_ROOT          — Arbor3D 倉庫路徑，嘗試呼叫其中的 postprocess 腳本
 *
 * 用法：node scripts/run-postprocess.mjs <jobDir> <scanId> [pathId]
 */
import { spawn } from "node:child_process";
import { runCloudDbh } from "./cloud-dbh-client.mjs";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");

const jobDir = process.argv[2];
const scanId = process.argv[3];
const pathId = process.argv[4] || "";

if (!jobDir || !scanId) {
  console.error("用法: node scripts/run-postprocess.mjs <jobDir> <scanId> [pathId]");
  process.exit(1);
}

function log(msg) {
  console.log(`[postprocess ${scanId}] ${msg}`);
}

async function dirHasFiles(dir) {
  try {
    const entries = await fs.readdir(dir, { recursive: true });
    return entries.some((name) => !name.startsWith("."));
  } catch {
    return false;
  }
}

async function runCmd(command, args, cwd, shell = false) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      shell,
      stdio: "inherit",
      env: process.env,
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${command} exited ${code}`));
    });
  });
}

async function main() {
  for (const name of ["raw", "denoised", "gaussian"]) {
    const ok = await dirHasFiles(path.join(jobDir, name));
    if (!ok) {
      throw new Error(`工作目錄缺少 ${name}/ 或內容為空：${jobDir}`);
    }
  }

  const cloudUrl = process.env.ARBOR3D_CLOUD_DBH_URL?.trim();
  const cloudKey = process.env.ARBOR3D_CLOUD_DBH_API_KEY?.trim() || "";
  if (cloudUrl) {
    await runCloudDbh({ baseUrl: cloudUrl, apiKey: cloudKey, jobDir, scanId, pathId, appRoot: root, log });
    log("雲端 DBH 完成");
    return;
  }

  const cmdTpl = process.env.ARBOR3D_CMD?.trim();
  if (cmdTpl) {
    const rendered = cmdTpl
      .replaceAll("{jobDir}", jobDir)
      .replaceAll("{scanId}", scanId)
      .replaceAll("{pathId}", pathId);
    log(`執行 ARBOR3D_CMD: ${rendered}`);
    await runCmd(rendered, [], root, true);
    log("ARBOR3D_CMD 完成");
    return;
  }

  const arborRoot = process.env.ARBOR3D_ROOT?.trim();
  if (arborRoot) {
    const candidates = [
      path.join(arborRoot, "scripts", "postprocess_from_inbox.py"),
      path.join(arborRoot, "scripts", "run_measure.py"),
      path.join(arborRoot, "run_postprocess.py"),
      path.join(arborRoot, "app", "postprocess.py"),
    ];
    let script = null;
    for (const candidate of candidates) {
      try {
        await fs.access(candidate);
        script = candidate;
        break;
      } catch {
        /* try next */
      }
    }
    if (!script) {
      throw new Error(
        `ARBOR3D_ROOT=${arborRoot} 找不到 postprocess 腳本。請設 ARBOR3D_CMD。`,
      );
    }
    log(`執行 ${script}`);
    const args = [script, "--job-dir", jobDir, "--scan-id", scanId];
    if (pathId) args.push("--path-id", pathId);
    const py =
      process.platform === "win32"
        ? process.env.PYTHON || "python"
        : "python3";
    await runCmd(py, args, arborRoot);
    log("Arbor3D 腳本完成");
    return;
  }

  const outScan = path.join(root, "public", "scans", scanId);
  const staged = path.join(outScan, "_inbox_staged");
  await fs.mkdir(staged, { recursive: true });
  for (const name of ["raw", "denoised", "gaussian"]) {
    const dest = path.join(staged, name);
    await fs.cp(path.join(jobDir, name), dest, { recursive: true, force: true });
  }
  await fs.writeFile(
    path.join(jobDir, "RESULT.md"),
    [
      `# 掃描 ${scanId} — 已收檔、待接量測管線`,
      "",
      "已確認：原始資料夾、去噪結果、高斯濺射。",
      "檔案已同步到：",
      `\`${path.relative(root, staged)}\``,
      "",
      "接上真管線後請設定其一再開跑：",
      "",
      "```bash",
      "export ARBOR3D_CLOUD_DBH_URL=https://<azure-container-app-fqdn>",
      "export ARBOR3D_CMD='python3 /path/to/Arbor3D/scripts/postprocess_from_inbox.py --job-dir {jobDir} --scan-id {scanId}'",
      "# 或",
      "export ARBOR3D_ROOT=/path/to/Arbor3D",
      "node scripts/run-postprocess.mjs",
      "```",
      "",
      "管線應產出：",
      `- src/data/inventories/${scanId}.json`,
      `- public/scans/${scanId}/{photos,masks,dbh,models,maps}/`,
      "- 並在 src/data/scanBindings.ts 綁定公園／路徑",
      "",
    ].join("\n"),
    "utf8",
  );
  log("未設定 ARBOR3D_CLOUD_DBH_URL／ARBOR3D_CMD／ARBOR3D_ROOT：已暫存資料，請接上量測腳本後重跑。");
  await fs.writeFile(
    path.join(jobDir, "pipeline-status.json"),
    JSON.stringify(
      {
        status: "pending_pipeline",
        message:
          "三包資料已就緒。請設定 ARBOR3D_CLOUD_DBH_URL、ARBOR3D_CMD 或 ARBOR3D_ROOT 以跑後續量測。",
        stagedDir: staged,
      },
      null,
      2,
    ),
    "utf8",
  );
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
