# Arbor3D 雲端胸徑（Cloud DBH）

## 最新：只使用既有 F1 的混合運算已實際驗證

使用者已選擇「只用既有免費資源，不新增付費資源」。因此不執行下方的私人 ACR／Container Apps 付費部署方案，不升級 F1。

已更新既有 `arbor3d-dbh-1ec69a14`，App Service plan 仍為 `arbor3d-dbh-plan` / F1，資源群組資源種類與數量維持原狀。`/health` 回 200，`/v1/capabilities` 明確回 `section_geometry_ready=true`、`full_pipeline_ready=false`，沒有 Torch／Open3D／YOLO 雲端模型。

目前分工：

- **本機**：YOLO 遮罩、相機對應、點雲投影、遮擋排除、地面扶正與截面擷取，及輸出圖片。
- **Azure F1**：沿用原演算法完成截面的圓擬合／虛擬卡尺候選與品質評估。`POST /v1/sections` 限 5,000 點、2 MB，具 API key 驗證；不傳整批原始照片與大型 PLY。
- **本機 App**：保存回傳的 Azure 運算編號、時間、輸入 SHA-256 與複核原因。正式 DBH 仍須通過品質校準，雲端計算本身不等於精度達標。

### 真實驗收證據

原始批次 `20260812070325`、Tree_001，使用原有 YOLO 遮罩與相機姿態，本機讀取 3,168,156 點原始場景，擷取後將截面送 Azure。

1. 直接驗證：22 個真實截面點，Azure 回覆時間約 0.687 秒，運算 ID `302cd173562f4dfb8b29a0955f652904`。
2. 管線驗證：重新從原始場景執行，21 個截面點，Azure 運算 ID `16cd3053f6ce49fe904fe475e43638c6`，本機前處理至輸出總計約 8.328 秒。

地面估計有隨機性，兩次切片略有不同，這些時間只是本次單木功能測試，不代表全園效能。實際使用的是備援高度，且未有人工真值校準，故兩次正式 DBH 均保持 null、待複核。未把候選 20.6／21.1 cm 宣稱為標準胸徑。

本機證據：`.runtime/free-geometry/azure-section-verification.json`、`.runtime/free-geometry/hybrid-pipeline/verification.json`、該目錄的 dbh_results.json 與截面圖。原始掃描檔未改寫。

### 啟用與限制

本機 `.env.local` 已設定 `ARBOR3D_SECTION_CLOUD_URL`、伺服器端 API key 及 `ARBOR3D_ROOT`。新真實資料匯入走本機正式前處理加 Azure 截面計算；模擬資料仍不送正式管線。全雲端 `ARBOR3D_CLOUD_DBH_URL` 未啟用。

部署腳本 `scripts/deploy_free_geometry.py` 只允許更新該既有 F1，不建立或升級資源。認證與部署設定保存在忽略追蹤的 .runtime；不得將其打包或提交 Git。F1 的休眠與 CPU 配額限制仍適用，不保證全天候服務。

本次 App 50 項、Python 50 項測試及正式建置通過。尚未重新辨識整園全部樹木，也未完成全園新匯入驗收。Copilot Studio 仍未啟用；這是 Azure 計算服務，不冒稱 Microsoft AI 代理已發布。

以下內容保留先前全雲端方案的設計紀錄，付費部署已依使用者要求暫停。舊文中「等待費用上限」已由「不新增付費資源」的決定取代。


把既有 `scripts/postprocess_from_inbox.py`（YOLO → DBH → 發佈盤點）接到 **Microsoft Azure Container Apps**，讓 App 用環境變數呼叫雲端，不必只在 Mac／本機跑。

## 2026-10-27 完整雲端管線接線進度

**程式接線已補齊，但尚未完成 Azure 上的真實批次量測驗收。** 舊 F1 服務仍是 prepare-only，不能宣稱已執行正式胸徑計算。

新增內容：

- 認證、串流上傳與大小限制、ZIP 路徑及解壓限制。
- 每個任務的資料與發佈目錄分離，避免同批次或不同使用者污染成果。
- `prepared` 與 `succeeded` 分開，只有正式管線產生非空盤點後才提供成果下載。
- 結果 ZIP、逐檔 SHA-256 清單、下載大小與雜湊核對，再安裝到本機 App 的 scans 與路線綁定。
- 雲端能力檢查必須確認模型、依賴、正式模式及成果下載；失敗不冒充計算成功。
- 保存雲端任務編號，重試時先查詢既有任務，避免斷線後重複提交。
- Docker CPU 版本採 Torch CPU wheel，保留 YOLO 與 Open3D 正式演算法；不是 GPU 部署，也不是 Copilot Studio 代理。

### 已確認的真實資料

使用者提供「OneDrive/桌面/環保局樹木專題」。`20260812070325` 含 47,523,162 bytes 去噪 PLY、491,101,537 bytes 完整 3DGS、292 張 JPG（894,487,905 bytes）、calib.json 及 583 筆相機姿態。已讀取校正與姿態 JSON 確認可解析，尚未上傳到 Azure。原始素材未修改。

`20260818092855` 雖有 PLY，但該位置缺少 cameras.json 與原始 JPG，因此不選作完整流程驗收批次。

### 部署準備與阻塞

- 私人部署來源包：`.runtime/cloud-deploy/source.zip`，由 `python scripts/package_cloud_deployment.py` 建立，含正式程式及 v3 模型，不含 .env、認證與原始掃描。
- `infra/azure/dbh-compute.bicep` 已通過 Bicep 編譯，要求非空 API key、私人 ACR、受控識別拉取映像。此版本最小副本為 1，以免背景任務在處理中被縮至 0；**執行期間會計費，驗收後必須停用運算副本**，不能宣稱閒置自動免費。
- 現有 F1 只有 1 GB 記憶體，不適合本批完整處理；尚未升級既有方案或新增付費資源。已向使用者詢問本次測試費用上限，等待答覆。
- 此電腦 Docker Desktop 啟動失敗，尚未建出或推送完整 Linux 映像。新增私人映像庫後仍須確認學生訂閱允許的建置方式；未假稱映像已可用。
- App 的正式雲端 URL 仍未啟用，避免導向只能準備檔案的舊端點。待部署及真實資料跑完、下載回 App 驗收後再設定。

### 本機檢查

App 49 項測試；Python 12 + 26 + Cloud 10 = 48 項；正式建置、Lint、ZIP 成果核對與 Bicep 編譯通過。單元測試使用測試夾具驗證傳輸與狀態，不等於真實點雲已在雲端量測完成。

以下保留舊版部署背景，遇到 prepared/succeeded 定義差異時，以上方 API v2 為準。

## 架構

```
App 匯入 inbox (raw / denoised / gaussian)
        │
        ▼
run-postprocess.mjs
  ├─ ARBOR3D_CLOUD_DBH_URL  →  POST zip → Cloud DBH API → 同支 Python 管線
  ├─ ARBOR3D_CMD            →  本機自訂指令
  └─ ARBOR3D_ROOT           →  本機 postprocess_from_inbox.py
```

演算法不改；只換執行位置。

## Windows 本機煙測 API

```powershell
cd <repo>
python -m pip install -r cloud_dbh/requirements.txt
$env:ARBOR3D_CLOUD_WORK_DIR = "$env:TEMP\arbor3d-cloud-jobs"
$env:ARBOR3D_CLOUD_PREPARE_ONLY = "true"
$env:PYTHONPATH = (Get-Location).Path
uvicorn cloud_dbh.app:app --host 127.0.0.1 --port 8080
```

App：

```env
ARBOR3D_CLOUD_DBH_URL=http://127.0.0.1:8080
```

`prepare_only=true` 只整理 inbox，不跑 PyTorch；適合無完整測量依賴時驗證 HTTP 閉環。

## 建置映像

```powershell
# 小：API + prepare-only
docker build -f cloud_dbh/Dockerfile.api -t arbor3d-cloud-dbh-api:latest .

# 大：含 requirements.txt（PyTorch／Open3D／YOLO）
docker build -f cloud_dbh/Dockerfile -t arbor3d-cloud-dbh:latest .
```

推到 Azure Container Registry 後，把 image 填進 Bicep 參數。

## Azure 部署（學生資源群組）

前置：`az login`、已有 `arbor3d-competition-rg`（或自訂）。

**注意（Azure for Students）：** 此訂閱常禁止 ACR Tasks，且資源須落在允許區域（本專案用 `eastasia`）。實務上改走 **App Service (Linux / Python 3.11)** zip 部署，不必本機 Docker。

目前已部署的 Cloud DBH（prepare-only）：

```
https://arbor3d-dbh-1ec69a14.azurewebsites.net
```

健康檢查：`GET /health` → `{"ok":true,"service":"arbor3d-cloud-dbh",...}`

App `.env.local`：

```env
ARBOR3D_CLOUD_DBH_URL=https://arbor3d-dbh-1ec69a14.azurewebsites.net
ARBOR_ALLOW_BILLABLE_CLOUD=NO
```

不用時可停站省費用：

```powershell
az webapp stop -g arbor3d-competition-rg -n arbor3d-dbh-1ec69a14
```

### Container Apps（有 ACR Tasks 配額時）

```powershell
az deployment group create `
  --resource-group arbor3d-competition-rg `
  --template-file infra/azure/dbh-compute.bicep `
  --parameters namePrefix=arbor3d `
               containerImage=<acr>.azurecr.io/arbor3d-cloud-dbh:latest `
               prepareOnly=true `
               apiKey=<optional-secret>
```

## GPU 與成本

| 環境 | 建議 |
|---|---|
| Azure for Students（常無 NC GPU） | `prepareOnly=true` 煙測；完整 DBH 在 Windows 本機 GPU 用 `ARBOR3D_ROOT` |
| 有 GPU 配額／付費 NC | 推 full Dockerfile，設 `prepareOnly=false`，`minReplicas=0` 省閒置費 |
| 競賽展示 | 預先跑完盤點 JSON；現場不要即時燒 GPU |

記得在 Cost Management 設 budget／alert（見 PROJECT_STATUS P1）。

## 驗收清單

- [ ] `GET /health` 回 `ok: true`
- [ ] App 設 `ARBOR3D_CLOUD_DBH_URL` 後，非 `sim*` 匯入走 `arbor3d` 模式（見 `importPipeline` 測試）
- [ ] `prepare_only` job 狀態到 `succeeded`
- [ ] Full image：真實 inbox 產出 `app/src/data/inventories/<scanId>.json`
- [ ] 未設 URL／CMD／ROOT 時仍明確 `pending_pipeline`，不靜默假裝已量測
