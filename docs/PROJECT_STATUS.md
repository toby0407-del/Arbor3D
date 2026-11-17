# Arbor3D 專案現況與後續路線圖

更新日期：2026-11-17。本文件是目前版本的單一進度入口；其他帶有舊日期、舊分支或模擬資料數量的文件只作歷史驗收紀錄。

## 目前結論

Arbor3D 的既有功能分支已整合至 `main`，Web App、匯入流程、品質複核、人工量測同步、分析匯出、Phi-4／RAG 助理及 Azure 持續部署均保留。正式發布的盤點資料已完成治理，目前只包含逢甲大學與惠來公園兩筆實地來源；所有過去生成的 `sim*` 盤點與配套媒體、分析、GPX、季度 CSV 均已移除。

系統目前可用於資料整理、盤點複核與工作流程展示，但仍不能宣稱已完成量測精度校準、真實跨期成長驗證或碳權認證。

## 發布盤點

| 地點 | scan_id | 發布棵數 | 路線 | 資料狀態 |
|---|---|---:|---|---|
| 逢甲大學 | `20260818092855` | 16 | 校園掃描路徑（8/18 · 7-11） | 實地掃描盤點；無 GPS，以相對座標沿路徑放置 |
| 惠來公園 | `20261020165350` | 18 | 東側弧形掃描路徑 | 實際匯入批次；52 個候選中納入 18、排除 34，目前為 `preview_point_cloud` 快速預覽 |

惠來資料不是模擬盤點，但快速預覽不等同正式 Arbor3D Python／YOLO／標準 1.3 m DBH 管線。其路線是使用者繪製的近似位置，仍待現場 GPX 更新。

目前發布目錄應保持以下不變量：

- `app/src/data/inventories/` 只有上述兩份 JSON。
- `app/public/scans/` 只有上述兩個掃描目錄及共用的逢甲實拍素材。
- `app/public/analysis/` 目前只有逢甲分析快照。
- `app/src/data/scanBindings.ts` 只綁定逢甲與惠來路線。
- `app/scripts/park-simulation-sites.json` 為空陣列。

`app/tests/inventoryCatalog.test.ts` 會在 CI 防止模擬盤點或額外發布資料未經審查重新混入。

## 2026-11-17 驗證結果

| 檢查 | 結果 |
|---|---|
| App 自動測試 | 63 項通過，0 失敗 |
| Lint | 通過；1 個既有測試檔 `no-unsafe-optional-chaining` 非阻斷警告 |
| Production build | TypeScript、Vite client 與 production server build 成功 |
| npm audit | 0 vulnerabilities |
| 本機 production server | `http://127.0.0.1:5174/`、`/healthz`、兩筆 inventory 資源皆回應 HTTP 200 |
| GitHub Actions | `main` 的資料清理提交已完成 Azure App Service 部署，結果 success |

本次只重跑 App 測試、lint 與 build；過去文件中的 Python 測試數字不是本次驗證結果，不應拿來代表 2026-11-17 狀態。

## 已完成能力

| 區塊 | 現況 |
|---|---|
| Web App | React 19、TypeScript、Vite 8、地圖搜尋、掃描路徑、盤點表、品質燈號、影像與 Three.js 點雲 |
| 正式匯入 | 接收去噪 PLY、高斯 PLY、照片、`calib.json`、`cameras.json`，可銜接本機或 Cloud DBH adapter |
| 現場複核 | 人工 DBH／樹高／日期／備註可離線保存，連線後同步 Cosmos DB；不覆蓋原始演算法值 |
| 品質治理 | 非標準胸高、缺測與品質不足維持待複核，不以信心分數冒充量測精度 |
| 分析輸出 | Analytics JSON／CSV／Excel、Power BI 資料包與圖表資料；真實誤差指標在沒有人工配對時保持空白 |
| AI 助理 | 本機證據規則、RAG、Foundry Local Phi-4 adapter 與 Copilot Studio adapter；未設定外部服務時安全退回本機模式 |
| Azure | App Service 持續部署、Cosmos adapter、既有 F1 Cloud DBH prepare／hybrid 路徑；秘密不進前端或 Git |
| 部署資料治理 | 已移除 29 組模擬盤點 JSON／掃描媒體、17 份模擬分析輸出、合成證據、模擬 GPX 與季度 CSV |

## 仍未完成或不可宣稱

- 尚無足量同樹、同日、標準 1.3 m 的人工 DBH 配對，因此 MAE、RMSE、準確率及通過率不可填造。
- 尚未完成第二期同路徑、固定樹號的真實掃描，因此跨期生長曲線不能稱為實測成長。
- 惠來批次仍是快速點雲預覽，需以正式 YOLO／DBH 管線重跑並人工驗收。
- 惠來路線需用現場 GPX 或 App 錄製軌跡取代近似手繪線。
- Copilot Studio 正式代理與 Entra 組織登入仍受 Microsoft 租戶權限／管理員核准影響。
- Power BI Desktop 本機驗證不等於 Fabric／Power BI Service 已發布。
- 碳匯是盤點估算，不是認證碳權、年度減碳量或樹木健康診斷。
- 完整雲端 YOLO／Open3D GPU 管線尚未正式部署；目前仍以本機重運算及既有免費混合服務為主。

## 下一步優先順序

### P0 — 真實資料閉環

1. 以正式 Arbor3D 管線重跑惠來 `20261020165350`，保存方法、版本、輸入雜湊與品質結果。
2. 在逢甲與惠來完成標準 1.3 m 人工 DBH、日期與固定樹號核對。
3. 取得現場 GPX，更新惠來東側路線的幾何與可靠性標示。
4. 完成第二期同路徑掃描，才能建立真實跨期成長資料。

### P1 — 正式帳號與分析服務

1. 由租戶管理員建立／核准 Entra App registration 與 App roles。
2. 決定是否發布 Power BI／Fabric；若發布，需先完成 RLS、容量、成本與展示帳號驗收。
3. 建立並發布 Copilot Studio Arbor3D 代理，驗證 Direct Line、DLP 與用量限制。
4. 統一正式 Cosmos 資源與 Managed Identity，評估移除重複的早期開發資源。

### P2 — 工程與戶外體驗

- 以手機實機驗證弱網、離線、GPS、單手操作與大量媒體載入。
- 將大型地點 JSON 與 3D viewer 持續做按需載入與 bundle 優化。
- 保留產生模擬輸入的開發工具，但不得把產物提交成正式盤點或分析快照。

## 啟動與部署

本機 production 模式：

```bash
cd app
npm ci
npm run build
PORT=5174 HOST=127.0.0.1 npm start
```

開發模式：

```bash
cd app
npm ci
npm run dev -- --host 127.0.0.1 --port 5174
```

公開網站：<https://arbor3d-platform-1ec69a14.azurewebsites.net>。`main` 每次推送會由 `.github/workflows/deploy-azure-app.yml` 執行測試、建置與部署；應以該次 GitHub Actions 結果判定是否已上線。

## 文件閱讀順序

1. [根目錄 README](../README.md)：專案定位、管線與整體功能。
2. [App README](../app/README.md)：介面操作、資料流與啟動方法。
3. [Microsoft 整合](microsoft/README.md)：分析、Azure、Power BI 與 AI adapter。
4. [Cloud DBH](microsoft/CLOUD_DBH.md)：免費混合運算範圍與限制。
5. [量測品質](../measurement_quality/README.md)：人工真值與精度驗收規則。

`docs/competition/`、舊版 Microsoft 驗證文件及帶有模擬資料數量的段落保留為歷史紀錄，不代表目前發布盤點內容。
