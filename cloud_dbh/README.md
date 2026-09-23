# Arbor3D Cloud DBH

把既有 `scripts/postprocess_from_inbox.py` 胸徑／盤點管線包成 HTTP 服務，部署到 **Azure Container Apps**，讓 App 用 `ARBOR3D_CLOUD_DBH_URL` 做雲端計算，而不是只在 Mac／本機 GPU 跑。

## 端點

| Method | Path | 說明 |
|---|---|---|
| GET | `/health` | 健康檢查 |
| POST | `/v1/jobs` | `multipart`: `scan_id`, `path_id?`, `prepare_only?`, `archive` (zip) |
| GET | `/v1/jobs/{job_id}` | 查詢狀態：`queued` / `running` / `succeeded` / `failed` |

Zip 內需含 `raw/`、`denoised/`、`gaussian/`（與 App inbox 相同）。

## 本機（Windows）快速煙測（不裝 PyTorch）

```powershell
cd cloud_dbh
python -m pip install -r requirements.txt
$env:ARBOR3D_CLOUD_WORK_DIR = "$env:TEMP\arbor3d-cloud-jobs"
$env:ARBOR3D_CLOUD_PREPARE_ONLY = "true"
uvicorn cloud_dbh.app:app --app-dir .. --host 127.0.0.1 --port 8080
```

另一個終端：

```powershell
curl http://127.0.0.1:8080/health
```

## Docker

```powershell
# API-only（prepare-only，體積小）
docker build -f cloud_dbh/Dockerfile.api -t arbor3d-cloud-dbh-api:latest .

# 完整 GPU／量測映像（多 GB，需 requirements.txt）
docker build -f cloud_dbh/Dockerfile -t arbor3d-cloud-dbh:latest .
```

## Azure 部署

見 [docs/microsoft/CLOUD_DBH.md](../docs/microsoft/CLOUD_DBH.md) 與 `infra/azure/dbh-compute.bicep`。

```bash
az deployment group create \
  --resource-group arbor3d-competition-rg \
  --template-file infra/azure/dbh-compute.bicep \
  --parameters namePrefix=arbor3d containerImage=<your-acr>/arbor3d-cloud-dbh:latest prepareOnly=true
```

部署後把輸出的 `cloudDbhBaseUrl` 寫進 App：

```env
ARBOR3D_CLOUD_DBH_URL=https://<fqdn>
ARBOR3D_CLOUD_DBH_API_KEY=<optional>
```

## 與本機管線的關係

- **不改** YOLO／Open3D／DBH 演算法；只換成遠端執行同一個 `postprocess_from_inbox.py`。
- `prepare_only=true`：只整理 inbox，適合無 GPU 的學生訂閱煙測。
- 完整胸徑計算需要映像內已安裝 repo 根目錄 `requirements.txt`（PyTorch／Open3D／Ultralytics），或在 Windows GPU 本機設 `ARBOR3D_ROOT`。
