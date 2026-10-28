# Arbor3D 專案現況與後續路線圖

## 最新：統一技術影像與本機交付

2026-10-28：465 棵展示樹的橫切面切換至固定正向座標圖；點雲預覽採深底離散散點，排除旋轉、調色與照片式替代。真實掃描附件未修改，展示圖仍保留來源識別。App 正式建置與 57 項測試通過；Python 一般／分析／雲端共 52 項通過。Desktop 三組報表可重新開啟、刷新及唯讀核對後更新 App。GitHub 使用 competition-quality-workflow 分支；本機交付與資料副本另存使用者指定桌面資料夾，未部署 Azure 前端。

## 最新：Power BI 報表複核與 AI 助理修正

2026-10-28：三組 Desktop 已實際刷新及核對 DAX，更新 19 份 App 快照；季度樹木數 295、觀測 4,720、最新需核對 30（10.17%，情境設定）。修正註記誤判、跨季碳存量重複累加、App／Desktop 碳量取值差異及圖表標題。真實逢甲仍 16 棵待人工核對，無有效實測配對。Phi-4 加強檢索與資料約束，七項實際問答通過。App 56 項及分析 Python 28 項通過。詳細範圍見 [Power BI 本機驗收](microsoft/POWERBI_LOCAL.md)。

## 歷史：Power BI Desktop 本機分析回到 App

2026-10-28 改用未登入的 Power BI Desktop；真實 16 棵與 18 座模擬公園 295 棵分別刷新與執行 DAX，再核對後匯出到 App 的分析區。App 顯示來源、計算時間與資料版本，資料變動會提醒重跑。這是當期分析快照，未開通線上 Power BI/Fabric，未更新 Azure 前端網站。操作及驗收範圍見 [本機 Power BI 流程](microsoft/POWERBI_LOCAL.md)。

## 最新：既有免費 Azure 混合運算已驗證

依使用者要求不新增付費資源。既有 DBH App Service 已更新，方案仍是 F1。真實 Tree_001 已跑通本機投影、地面扶正與截面擷取，再由 Azure 計算幾何／品質，回本機輸出紀錄與圖。App 已設定混合運算，沒有啟用全雲端 YOLO／Open3D 或 Copilot Studio；品質未校準及非標準胸高結果仍待複核。App 50、Python 50 項測試通過。詳見 [雲端最新狀態](microsoft/CLOUD_DBH.md)。

最新程式以 `competition-quality-workflow` 分支管理。Azure 前端網站仍維持原版本；既有 DBH API 已更新為免費混合計算服務。

以下為歷次紀錄，出現等待預算的文字時以上方使用者免費資源限制為準。


## 2026-10-27 Azure 正式量測續作

雲端 API v2、正式成果下載與逐檔校驗、每任務資料隔離及 App 安裝回查已實作。找到使用者完整 20260812070325 原始批次，尚未上傳、部署或完成真實雲端量測。仍等待新增運算資源的測試費用上限；本機 Docker Desktop 也未能啟動，尚未建置 Linux 映像。不能標示為「Azure 雲端代理已完成量測」。本機 App 49 項、Python 48 項測試及正式建置通過。詳見 [雲端量測進度](microsoft/CLOUD_DBH.md)。

## 2026-10-27 Microsoft 串接更新

本次續作已完成手測逐欄同步、離線待同步保存與重試、Cosmos ETag 並行合併、真實連線狀態顯示，並修正桌面窄視窗被橫向提示阻擋的問題。App 47 項測試與 Python 39 項通過，另有真實 Phi-4 問答、Cosmos 並行寫入讀回及瀏覽器驗證。

- 依使用者要求移除比賽導覽與首頁專用展示入口，保留一般操作及品質／補掃功能。
- 已在本機以 Foundry Local 官方 SDK 啟動 GPU Phi-4 mini，原生推論及 App API 均已取得真實模型回答。
- 既有 Cosmos DB 已完成獨立連線測試文件的建立、讀回、刪除；App 服務亦能讀取容器。沒有修改原始樹木觀測來製造驗證結果。
- **Power BI 暫緩**：學校 Microsoft 365 租戶關閉 Fabric Free 自行註冊，使用者將聯絡校方。依使用者指示先跳過，不能標示為已串接。
- **Entra 登入未完成**：建立應用程式遭租戶權限拒絕；等待管理員核准的 Client ID／Tenant ID。目前 App 使用本機帳號，資料庫透過已登入的 Azure CLI 身分存取。
- 人工真值、跨期實測及經驗品質邊界仍待取得；不宣稱已完成精度校準。

實際設定、啟動與阻塞項目見 [Microsoft 連線紀錄](microsoft/LIVE_CONNECTIONS.md)。本機修改尚未推送或更新 Azure。下方為歷史紀錄。

更新日期：2026-09-24。這份文件是競賽展示、開發交接與驗收的單一進度入口；技術細節仍以各子目錄文件為準。

## 本次公園模擬更新

- 學校只保留逢甲大學掃描路線；其他 12 所學校示範綁定已移除，歷史檔保留。
- 新增上安、上德、上石、世斌、世貿、中清 6 座公園，共 18 個公園／綠地場景、295 棵、4,720 筆季度紀錄（2022 Q3–2026 Q2）。
- App 可切換單木查看 16 季模擬手測、AI 胸徑、樹高、日期、固定樹號與座標；成長曲線直接使用儲存的季度值，可匯出全園季度 CSV。
- 補齊模擬 GPX 與可重建分析資料包。新增公園的 GPX 是示意軌跡，地圖不把它畫成已驗證步道。現有公園保留既有 OSM 參考線。
- 逢甲原始掃描 JSON 未修改；真實人工胸徑與第二期真實掃描仍未取得。來源照片／橫切面／點雲預覽僅供參考，不宣稱是其他公園實拍。
- 全部欄位與假設、重建方式見 [公園模擬資料說明](../app/scenarios/parks/README.md)。本機分析輸出位於 `outputs/parks-simulated-20260923/analytics`，未進 Git。

本次驗證：2026-09-24 最新版本 App 32 項測試、production build 與 Lint 通過；包含 Foundry Local Phi-4、Azure Phi-4 HTTPS adapter、Copilot Studio、Power BI 圖表匯出與退回行為。Power BI 五頁 PBIP/PBIR 共 50 個定義檔通過 Microsoft schema cache 驗證，但仍未完成 Desktop 刷新、DAX 執行與版面驗收。展示登入、HttpOnly Session、人工量測寫入／讀回與登出失效另有 API 端到端驗證。首頁主程式約 194 KB，10,462 筆地點為獨立 JSON，31 份盤點、MSAL 與 3D 點雲引擎均按需載入。

## 目前結論

Arbor3D 已具備可展示的 **Physical → Digital → AI** 主流程、真實盤點介面、Microsoft AI/Data 離線分析層，以及通過自動測試的 Copilot Studio 串接層。現在可以從逢甲大學示範路徑查看 16 棵樹、影像／點雲、DBH 與碳匯資料，並在 App 內向 AI 助理詢問待複核項目及後續行動。Copilot Studio 代理仍待租戶建立、發布及填入 Token Endpoint，現階段未宣稱已連線上線。

目前仍不能宣稱「完整實地長期監測已完成」：只有一期真實掃描，沒有第二期同樹實測、固定樹號與標準 1.3 m 人工 DBH，因此精度 KPI 與真實生長量仍應保持空白。

## 已完成

| 區塊 | 完成內容 | 驗證狀態 |
|---|---|---|
| 實體與數位盤點 | YOLO 樹幹分割、單木 ID、DBH、3DGS／PLY、JSON／CSV／HTML | 已有逢甲 2026-08-18 真實示範資料，16 棵 |
| Web App | Microsoft Entra／展示登入、HttpOnly Session、地圖搜尋、可靠性標示路線、盤點表、燈號、影像、3D、手測、CSV、碳匯；地點、盤點、MSAL 與 3D 按需載入 | App 32 項測試、production build 與 Lint 通過；Azure App Service 網址已建立，`main` 推送後由 GitHub Actions 自動驗證及更新；正式密碼不進 App |
| 帳號與手測後端 | Entra ID MSAL + PKCE、JWT issuer/audience/signature、App roles、8 小時伺服器 Session；人工 DBH／樹高／日期離線保存並同步 Cosmos DB | Cosmos adapter、Bicep 與 Japan East Serverless 資源已驗證；Entra App registration 仍受學校租戶目錄權限限制，正式登入尚未啟用 |
| 正式匯入閉環 | App 接收 PLY、照片、`calib.json`、`cameras.json`；adapter 自動整理既有資料目錄、執行 Python、發佈附件並綁定路徑；可改走 `ARBOR3D_CLOUD_DBH_URL` 雲端 DBH | adapter 測試含雲端 URL 選路；Cloud DBH FastAPI + Bicep 已就緒；完整 GPU 映像待 ACR／配額 |
| 雲端 DBH（Microsoft） | `cloud_dbh/` HTTP API 包裝 `postprocess_from_inbox.py`；App Service `arbor3d-dbh-1ec69a14`（eastasia、F1）；App 設 `ARBOR3D_CLOUD_DBH_URL` | `/health` 已驗；prepare-only。學生訂閱無 ACR Tasks／常無 GPU；完整胸徑用本機 GPU + `ARBOR3D_ROOT` |
| 合成展示影像 | 由逢甲實圖＋既有 4 組合成圖衍生 **12×3** 張 DEMO 標示影像；`simulate:media:expand` | `simulatedMedia` 3 項測試通過 |
| Azure 成本防護 | 訂閱年預算 `arbor3d-100usd`＝**100 USD**，50／80／100% 與預測告警寄至學生帳號 | 已建立；請在 portal Cost Management 再確認通知 |
| DEMO 完整度 | 30 組模擬檔（18 個啟用公園場景、12 個停用學校歷史檔）使用 12 張新合成素材：4 種分割圖、4 種胸高橫切面、4 種點雲側視，獨立分派後形成最多 64 種組合；另附 900 點示意 PLY | 31 組目前發布資料共 481 棵皆有可載入橫切面；新匯入只要包含橫切面，就強制同批每棵樹完整，否則拒絕發布 |
| 分析資料層 | Analytics JSON／CSV、資料契約、誤差與跨期規則；Excel 僅作資料快照與交叉核對 | Python 26 項測試通過；真實／模擬資料分離 |
| Power BI／Fabric | Power BI 作為主要分析輔助；App 可匯出分析輸入 JSON、**圖表 CSV 包**（燈號／胸徑／KPI）與盤內圖表預覽；另可產生五頁 PBIP | 圖表匯出測試通過；Desktop 畫面驗收仍待 |
| App AI 助理 | Foundry Local Phi-4／Azure Phi-4 Managed Compute／Copilot Studio＋本機證據模式兜底；1,000 題 RAG | 本機與雲端 Phi-4 adapter、Direct Line adapter 及退回行為通過測試；已產生 900 訓練／100 保留評測的 QLoRA 資料；實際微調與雲端 GPU deployment 待配額、硬體及成本確認 |
| Azure Foundry | 曾完成 Azure for Students 資源、project 與 `gpt-4.1-mini` deployment 驗證 | 保留為技術驗證紀錄；正式網站已移除 Azure AI endpoint/model，不直接呼叫 GPT |
| 安全與依賴 | `.env.local` 不進 Git、瀏覽器拿不到金鑰、Node 依賴稽核 | `npm audit` 0 vulnerabilities |

Azure 實際部署資訊與停止費用方式見 [Microsoft Azure 部署紀錄](microsoft/AZURE_DEPLOYMENT.md)。

## 待完成與優先順序

### 台中展示替代層（已完成）

- 範圍固定為台中 18 個公園／綠地場景；產生器會拒絕超出台中座標範圍的場景。
- 295 棵樹均有 2022 Q3–2026 Q2 共 16 季的歷史推估，合計 4,720 筆。
- 每季包含季末日期、標準 1.3 m 模擬人工 DBH、模擬 AI DBH、模擬樹高、位置與固定樹號。
- 同棵樹跨季以 `persistent_tree_id` 連接，可展示 steady、slow、stalled 與 negative_review 成長情境。
- 上述完成的是展示與 Power BI 分析輔助資料；下一節的真實掃描、人工量測與 GPX 仍是正式驗證條件。

### P0 — 競賽可信度與真正閉環

| 任務 | 為什麼必要 | 完成條件 |
|---|---|---|
| 用新掃描驗收正式 Arbor3D 匯入閉環 | App、校正／姿態輸入、正式 adapter 與自動發佈已完成；未設定正式環境時仍明確使用快速預覽 | 取得下一趟真實素材，在具 PyTorch／Open3D／Ultralytics 的環境跑完，並確認 App 出現正式結果 |
| 完成第二期同路徑真實掃描 | 現在只有一期，成長曲線不能當作實測結果 | 至少兩期掃描、同樹固定 ID 經人工確認，可產生真實 FactGrowth |
| 補標準 1.3 m 人工 DBH 與日期 | 沒有人工配對時，MAE／RMSE 不可計算 | 完成現場複核並匯出分析 bundle；有效配對數大於 0 |
| 用現場 GPX 取代暫定路線 | 目前啟用逢甲與 18 個公園／綠地；保留 13 條既有 OSM 參考線，6 座新公園未繪製推測線，其他學校路線已停用。模擬 GPX 與座標不算現場證據 | 實際 GPX／App 錄製軌跡完成並核對樹序 |

### P1 — 正式使用與 Microsoft 展示

| 任務 | 完成條件 |
|---|---|
| Windows Power BI Desktop 驗收 | 實際刷新 Power Query、驗證 DAX、關係、空值語意及五頁版面，再決定是否發佈 |
| Fabric／Power BI 雲端發佈決策 | 確認學生訂閱能力、容量、成本、RLS 與展示帳號後才部署；目前不宣稱已發佈 |
| Azure 成本防護 | **已設訂閱年預算 `arbor3d-100usd`＝100 USD**（50／80／100% 與預測告警）；請持續在 Cost Management 監控 |
| Copilot Studio 正式啟用 | 在 Microsoft 租戶建立並發布 Arbor3D 代理、開啟 Mobile app channel、填入 Token Endpoint，依組織政策完成 Entra／DLP／用量驗收 |
| Entra／Cosmos 正式部署 | **主要 Cosmos 已部署** `arbor3dcos483bd05e16`（Japan East）＋`Arbor3D`／`FieldMeasures`。另有早期開發帳號 `arbor3d-d1322855`，兩者皆為 Serverless、停用 local auth；正式環境應統一使用主要帳號，再評估移除重複開發資源。Entra App registration 需租戶目錄權限（學生帳目前不足），待管理員建立後填 client id |
| Cloud DBH 上線 | **已上線** App Service `https://arbor3d-dbh-1ec69a14.azurewebsites.net`（F1、prepare-only），`.env.local` 已填 URL；完整 GPU 胸徑仍待本機或配額 |
| Arbor3D 網站持續部署 | **已建立** `https://arbor3d-platform-1ec69a14.azurewebsites.net`，共用既有 F1 plan；GitHub `main` 每次 push 自動測試、build、deploy，Managed Identity 連接 Cosmos；AI 指定使用 Copilot Studio |

### P2 — 場域體驗與工程優化

- 手機戶外單手操作與地圖全螢幕仍需更多實機驗收。
- PWA manifest、Service Worker、已開啟頁面／影像／地點 JSON 快取及離線提示已完成；現場人工量測保留在裝置，恢復連線後會重試同步至 Cosmos DB；本機開發使用 file fallback。
- 全臺 10,462 筆地點已改為獨立 JSON；31 份盤點依路線載入，3D 引擎只在開啟點雲時載入。若未來目錄顯著成長，再依縣市切成多檔與伺服器搜尋。
- 清出至少 12 GiB 空間後，再安裝完整 PyTorch／Open3D／Ultralytics 管線並重跑 GPU 驗證；或改用 Windows GPU／Azure Cloud DBH full image。
- Docker 化本機 RAG／分析服務屬選配；**Cloud DBH**（`cloud_dbh/`）已提供量測管線的容器與 Bicep，不是 App 展示必要條件但為正式匯入雲端路徑。

## 模擬資料界線

目前缺少的展示媒體已用可重建的合成檔補齊，目的是讓影像、3D、上傳與盤點互動能完整演示。這些資料以 `dataset_kind=simulated`、`sim*` 掃描 ID、畫面警告及資產內 `DEMO / SIMULATED` 標記隔離。它們不會補足真實的第二期掃描、人工 1.3 m DBH、現場 GPX 或精度 KPI；上述項目仍須現場取得。

## 本機展示方式

```bash
cd app
npm install
npm run dev -- --host 127.0.0.1 --port 5324 --strictPort
```

開啟 `http://127.0.0.1:5324/`，按「示範登入」，搜尋「逢甲大學」，選擇「校園掃描路徑（8/18 · 7-11）」。也可使用示範帳號 `E-1027`／`arbor1027`。

若 `.env.local` 已填入 Copilot Studio Mobile app Token Endpoint 並開啟費用鎖，AI 助理會使用 Copilot；`copilot` 模式失敗時只退回本機證據模式。正式網站不設定 Azure AI endpoint/model。

## 驗收界線

- 現有 16 棵是真實掃描，但目前跨期曲線中的非基準時間點不得說成真實觀測。
- 碳匯是盤點估算，不是認證碳權、年度減碳量或健康診斷。
- Power BI 專案檔與 schema 已驗證，不等於已在 Power BI Desktop 完成畫面與 DAX 引擎驗收。
- Git 不保存原始大型點雲、完整高斯、Azure 金鑰、訂閱 ID 或個人帳號。
