# macOS 競賽開發環境

更新日期：2026-09-22。本文件區分「App／Microsoft 整合必需」與「完整 3D／YOLO 管線選配」，避免為了展示介面就安裝數 GB 的模型依賴。

## 本機已安裝並驗證

| 工具 | 用途 | 本機狀態 |
|---|---|---|
| Node.js + npm | React/Vite App、Excel 匯出、測試 | 已安裝；`app/node_modules` 已可用 |
| Python 3.11 | Foundry SDK、Power BI JSON schema 驗證 | 已安裝 |
| Azure CLI 2.90.0 | Azure 登入、訂閱與資源查詢 | 已安裝；尚未登入 |
| `azure-ai-projects` / `azure-identity` | Microsoft Foundry adapter | 已裝在專案 `.venv` |
| `jsonschema` 4.26.0 | PBIP/PBIR 官方 schema 驗證 | 已裝在專案 `.venv` |
| GitHub CLI | 推送與 Pull Request | 已登入 `toby0407-del` |

重建輕量環境：

```bash
brew install azure-cli python@3.11
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install \
  -r agents/requirements-foundry.txt \
  -r powerbi/requirements-validation.txt
npm ci --prefix app
```

驗證：

```bash
az version
.venv/bin/python -m agents.foundry '可以把估算碳量當碳權嗎？'
.venv/bin/python -m unittest discover -s analytics/tests -v
npm test --prefix app
npm run build --prefix app
npm run lint --prefix app
```

## Azure 接續步驟

安裝 CLI 不等於登入或建立資源。後續由帳號持有人執行：

```bash
az login
az account show
```

確認 Azure for Students 訂閱後，再於 Foundry 建立或選擇模型 deployment。App 設定依 `app/.env.example`；金鑰不得使用 `VITE_` 前綴或提交到 Git。

## 尚未安裝的重型管線

`requirements.txt` 包含 PyTorch、Open3D、Ultralytics、OpenCV 與 Transformers。這批依賴用於重新執行點雲、YOLO 與 SegFormer，不是展示既有盤點與 AI 助理的必要條件。

2026-09-22 安裝前本機資料磁碟僅餘約 4.2 GiB；Homebrew 清理後約 7.1 GiB，仍未達安全門檻，因此未安裝完整重型管線，以免填滿系統磁碟。建議先保留至少 12 GiB 可用空間，再執行：

```bash
.venv/bin/python -m pip install -r requirements.txt
```

## Power BI 與 Docker

- Power BI Desktop 沒有 macOS 版本；本機只做 PBIP/PBIR schema、資料契約與測試，最終 DAX、Power Query 刷新和畫面驗收移交 Windows Power BI Desktop。
- Docker 只用於可選的離線 RAG 容器示範，並非 App、Foundry SDK 或 Power BI 專案產生器的必要條件；目前未安裝。
