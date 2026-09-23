# Arbor3D 雲端胸徑（Cloud DBH）

把既有 `scripts/postprocess_from_inbox.py`（YOLO → DBH → 發佈盤點）接到 **Microsoft Azure Container Apps**，讓 App 用環境變數呼叫雲端，不必只在 Mac／本機跑。

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
